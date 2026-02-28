"""
PPT Generation Executor
读取 plan 并调用 Nano Banana 2 生成最终 PPT
支持分页执行、并发生成、分辨率可选
"""
import os
import sys
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from nano_banana_ppt.core.generator import PPTGenerator, _fix_black_corners
from nano_banana_ppt.core.data_visualizer import render_chart_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 并发生成时最大工作线程数，避免 API 限流
MAX_PARALLEL_WORKERS = 2  # Reduced from 3 to 2 for better stability


def _generate_single_slide(slide, visual_plan, slides_dir, generator, resolution, masters, clean_background_image=None):
    """
    单页生成逻辑，供串行或并行调用
    masters: dict {'content': img, 'section': img, 'hero': img}
    """
    # Check for table data first
    table_data = slide.get('table_data') or slide.get('text_content', {}).get('table_data')
    visualization = slide.get('visualization', '')
    
    if table_data:
        # 混合策略：表格用原生 PPT 表格（不渲染图）；图表用图片
        if visualization in ('bar', 'line', 'pie'):
            try:
                bg_img = clean_background_image if clean_background_image else None
                image = render_chart_image(table_data, visualization, slide.get('style_config', {}), background_image=bg_img)
                page_num = slide['page_num']
                slide_path = slides_dir / f"slide_{page_num:02d}.png"
                image.save(slide_path, "PNG")
                return page_num, image
            except Exception as e:
                logger.error(f"Failed to render chart for slide {slide.get('page_num')}: {e}")
                raise e
        else:
            # 表格页：跳过渲染，generator 将插入原生 PPT 表格
            page_num = slide['page_num']
            logger.info(f"  📋 Table slide P{page_num}: 使用原生 PPT 表格（可编辑）")
            # 不写入 images_dict，generator 检测到 table_data + 无图 时会插入原生表格
            return page_num, None

    prompt = slide['visual_prompt']
    reference_images = []

    # 1. 尝试加载显式指定的模版参考图
    if slide.get('reference_image') and os.path.exists(slide['reference_image']):
        try:
            ref_img = Image.open(slide['reference_image'])
            reference_images = [ref_img]
        except Exception as e:
            logger.warning(f"无法加载参考图: {e}")

    # 2. 如果没有模版参考图，尝试使用同类型的母版 (AI Minting Consistency)
    if not reference_images:
        p_type = slide.get('type')
        # Map page types to master keys
        if p_type == 'content':
            master_img = masters.get('content')
        elif p_type == 'section':
            master_img = masters.get('section')
        elif p_type == 'hero':
            master_img = masters.get('hero')
        else:
            master_img = None
            
        if master_img:
            reference_images = [master_img]

    is_background_only = slide.get('type') == 'background_only'
    image = generator.generate_image(
        prompt, aspect_ratio="16:9",
        reference_images=reference_images,
        is_background_only=is_background_only,
        resolution=resolution,
    )
    page_num = slide['page_num']
    slide_path = slides_dir / f"slide_{page_num:02d}.png"
    image.save(slide_path, "PNG")
    return page_num, image


def execute_plan(plan_file: str, output_name: str = "Final_Presentation",
                 template_path: str = None, project_dir: str = None,
                 resolution: str = "1K", slide_filter: list = None,
                 reassemble_only: bool = False):
    """
    Args:
        plan_file: 视觉计划 JSON 路径
        output_name: 输出 PPT 文件名（不含扩展名）
        template_path: PPTX 模版路径（可选）
        project_dir: 项目工作目录
        resolution: 分辨率 "1K"|"2K"|"4K"，默认 1K
        slide_filter: 仅重跑指定页号列表，如 [3,5,7]；None 表示全部生成
    """
    if not os.path.exists(plan_file):
        print(f"❌ 找不到计划文件: {plan_file}")
        return

    with open(plan_file, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    visual_plan = raw if isinstance(raw, list) else raw.get("slides", raw)
    meta = raw.get("meta", {}) if isinstance(raw, dict) else {}

    proj = Path(project_dir) if project_dir else Path(meta.get("project_dir", "output"))
    slides_dir = proj / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    ppt_dir = Path("output") / "ppt"
    
    # 尝试从项目目录推断 ppt_dir（如果是统一的日期格式目录）
    if proj.parent.name == "ppt":
        ppt_dir = proj.parent
    else:
        ppt_dir.mkdir(parents=True, exist_ok=True)
    
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    generator = PPTGenerator(api_key, api_base, slides_dir=str(slides_dir))

    resolution = (resolution or "1K").strip().upper()
    if resolution not in ("1K", "2K", "4K"):
        resolution = "1K"

    images_dict = {}
    
    # reassemble_only: 仅从已有 slides 重新组装 PPTX，不调 API
    if reassemble_only:
        print("\n📦 仅重新组装模式：从 slides/ 加载图片，不生成新图")
        for slide in visual_plan:
            pn = slide['page_num']
            path = slides_dir / f"slide_{pn:02d}.png"
            if path.exists():
                try:
                    img = Image.open(path).convert("RGB")
                    img = _fix_black_corners(img)
                    images_dict[pn] = img
                except Exception as e:
                    logger.warning(f"无法加载 {path}: {e}")
        missing = [s['page_num'] for s in visual_plan if s['page_num'] not in images_dict and not (s.get('table_data') or s.get('text_content', {}).get('table_data'))]
        if missing:
            print(f"⚠️ 缺少图片: 第 {missing} 页，将跳过或留白")
        date_prefix = date.today().strftime("%Y%m%d")
        output_path = proj / f"{date_prefix}_{output_name}.pptx"
        generator.create_advanced_pptx(visual_plan, images_dict, str(output_path), template_path)
        print(f"\n✅ PPT 重新组装完成: {output_path}")
        return str(output_path)
    
    # 风格母版字典：用于存储各类页面的第一张图，作为后续同类页面的参考
    masters = {
        'content': None,
        'section': None,
        'hero': None
    }

    # 分页执行：加载已有图片
    if slide_filter is not None:
        slide_set = set(slide_filter)
        for slide in visual_plan:
            pn = slide['page_num']
            if pn in slide_set:
                continue
            path = slides_dir / f"slide_{pn:02d}.png"
            if path.exists():
                try:
                    img = Image.open(path).convert("RGB")
                    img = _fix_black_corners(img)
                    images_dict[pn] = img
                except Exception as e:
                    logger.warning(f"无法加载已存在图片 {path}: {e}")
        to_run = [s for s in visual_plan if s['page_num'] in slide_set]
        print(f"\n🔄 分页重跑: 仅重新生成第 {sorted(slide_set)} 页，共 {len(to_run)} 页")
    else:
        to_run = visual_plan

    print(f"\n🚀 开始执行生成任务，分辨率 {resolution}")
    print(f"📂 项目目录: {proj}")
    if to_run != visual_plan:
        print(f"📄 待生成: {len(to_run)} 页（其余从缓存加载）")

    clean_background_image = None

    # Helper: Check if master needs to be loaded from cache
    def try_load_master(p_type):
        if masters[p_type] is None:
            # Find first page of this type without explicit reference
            for s in visual_plan:
                if s.get('type') == p_type and not s.get('reference_image'):
                    # If this page is cached (in images_dict), use it as master
                    if s['page_num'] in images_dict:
                        masters[p_type] = images_dict[s['page_num']]
                        print(f"  - 从缓存加载 {p_type} 母版 (Page {s['page_num']})")
                    break

    # 1. 尝试从缓存加载母版
    try_load_master('content')
    try_load_master('section')
    try_load_master('hero')

    # 2. 尝试加载 clean_background_image
    for s in visual_plan:
        if s.get('type') == 'background_only':
            if s['page_num'] in images_dict:
                clean_background_image = images_dict[s['page_num']]
            break

    # 3. 识别需要优先生成的种子页 (Seeds)
    # 种子页定义：某种类型的第一张无参考图页面，且当前尚未获取到 master
    seed_indices = []
    
    # Check Background Seed
    bg_idx = None
    for i, s in enumerate(to_run):
        if s.get('type') == 'background_only':
            bg_idx = i
            break
            
    if bg_idx is not None and clean_background_image is None:
        seed_indices.append(('background', bg_idx))

    # Check Style Seeds
    for p_type in ['content', 'section', 'hero']:
        if masters[p_type] is None:
            for i, s in enumerate(to_run):
                if s.get('type') == p_type and not s.get('reference_image'):
                    # Ensure this index isn't already marked (unlikely but safe)
                    if not any(idx == i for _, idx in seed_indices):
                        seed_indices.append((p_type, i))
                    break

    # Sort seeds by index to keep some order, though specific order doesn't matter much
    seed_indices.sort(key=lambda x: x[1])
    
    # Phase 1: 串行生成种子页
    if seed_indices:
        print(f"\n🌱 正在生成风格种子页 (共 {len(seed_indices)} 页)...")
        indices_to_remove = []
        
        for p_type, idx in seed_indices:
            slide = to_run[idx]
            print(f"  > [{p_type.upper()}] Generating Page {slide['page_num']}...")
            try:
                # Pass current masters state (some might be None, that's expected for seeds)
                _, img = _generate_single_slide(
                    slide, visual_plan, slides_dir, generator, resolution, masters, clean_background_image
                )
                images_dict[slide['page_num']] = img
                
                # Register as master/background
                if p_type == 'background':
                    clean_background_image = img
                    print("    -> 已设定为纯净背景")
                else:
                    masters[p_type] = img
                    print(f"    -> 已设定为 {p_type} 母版")
                
                indices_to_remove.append(idx)
                
            except Exception as e:
                logger.error(f"种子页生成失败: {e}")
                images_dict[slide['page_num']] = Image.new('RGB', (1920, 1080), color='gray')
                indices_to_remove.append(idx) # Still remove to avoid infinite loop or errors

        # Remove processed seeds from to_run (in reverse order to preserve indices)
        for idx in sorted(indices_to_remove, reverse=True):
            to_run.pop(idx)

    # Phase 2: 并行生成剩余页
    def run_one(s):
        pn = s['page_num']
        # Try up to 2 times at the executor level (in addition to generator retries)
        max_exec_attempts = 2
        for attempt in range(max_exec_attempts):
            try:
                return _generate_single_slide(s, visual_plan, slides_dir, generator, resolution, masters, clean_background_image)
            except Exception as e:
                logger.warning(f"Page {pn} Executor attempt {attempt+1}/{max_exec_attempts} failed: {e}")
                if attempt < max_exec_attempts - 1:
                    import time
                    time.sleep(5)  # Wait 5 seconds before executor-level retry
        
        logger.error(f"Page {pn} FINAL FAILURE after {max_exec_attempts} attempts.")
        # Return gray placeholder only after all retries fail
        return pn, Image.new('RGB', (1920, 1080), color='gray')

    if to_run:
        print(f"\n🚀 并行生成剩余 {len(to_run)} 页...")
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as ex:
            futures = {ex.submit(run_one, s): s for s in to_run}
            for i, fut in enumerate(as_completed(futures)):
                s = futures[fut]
                try:
                    pn, img = fut.result()
                    images_dict[pn] = img
                    print(f"  [{i+1}/{len(to_run)}] Page {pn} 完成")
                except Exception as e:
                    logger.error(f"Page {s['page_num']} 异常: {e}")

    date_prefix = date.today().strftime("%Y%m%d")
    output_path = proj / f"{date_prefix}_{output_name}.pptx"
    generator.create_advanced_pptx(visual_plan, images_dict, str(output_path), template_path)

    print(f"\n✅ PPT 生成完成: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    pass
