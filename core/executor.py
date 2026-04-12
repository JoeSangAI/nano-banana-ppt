"""
PPT Generation Executor
读取 plan 并调用 Nano Banana 2 生成最终 PPT
支持分页执行、并发生成、分辨率可选
"""
import os
import sys
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from tools.nano_banana_ppt.core.generator import PPTGenerator, _fix_black_corners
from tools.nano_banana_ppt.core.data_visualizer import render_chart_image
from tools.nano_banana_ppt.core.failure_classifier import (
    classify_failure, generate_failure_summary, FailureReport, FailureType, FailureSeverity
)
from tools.nano_banana_ppt.utils.provider_config import get_llm_api_base, get_llm_api_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 页面类型家族常量
CONTENT_FAMILY = {'content', 'framework', 'flowchart', 'comparison', 'data', 'toc', 'breathing', 'infographic'}
BOOKEND_FAMILY = {'cover', 'back', 'ending'}
POSITION_BOUNDING_BOXES = {
    "full": {"left": 0.0, "top": 0.0, "width": 1.0, "height": 1.0},
    "center": {"left": 0.2, "top": 0.2, "width": 0.6, "height": 0.6},
    "left": {"left": 0.0, "top": 0.2, "width": 0.4, "height": 0.6},
    "right": {"left": 0.6, "top": 0.2, "width": 0.4, "height": 0.6},
    "top": {"left": 0.2, "top": 0.0, "width": 0.6, "height": 0.4},
    "bottom": {"left": 0.2, "top": 0.6, "width": 0.6, "height": 0.4},
}
MODE_RESERVED_REGIONS = {
    "ELEMENT_PRESERVE": {"x": 0.2, "y": 0.2, "width": 0.6, "height": 0.6},
    "ORIGINAL_PRESENT": {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.9},
}

# 并发生成时最大工作线程数，避免 API 限流
MAX_PARALLEL_WORKERS = 2  # Reduced from 3 to 2 for better stability


def _infer_seed_family(slide_type: str) -> Optional[str]:
    slide_type = (slide_type or "content").strip().lower()
    if slide_type == "background_only":
        return "background_only"
    if slide_type == "section":
        return "section"
    if slide_type in {"cover", "back", "ending", "hero", "quote"}:
        return "hero"
    if slide_type in CONTENT_FAMILY or slide_type not in BOOKEND_FAMILY:
        return "content"
    return None


def _convert_new_format_to_slides(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将新的 visual_plan.json 格式（pages 数组）转换为旧格式的 slides 数组

    新格式：
    {
        "pages": [
            {
                "page_number": 1,
                "title": "第 1 页 · 标题",
                "images": [
                    {
                        "path": "output/images/xxx.png",
                        "mode": "INTENT_FUSION",
                        "role": "装饰图片",
                        "position": "center",
                        "final_visual_prompt": "生成的完整 prompt"
                    }
                ]
            }
        ]
    }

    旧格式：
    [
        {
            "page_num": 1,
            "type": "content",
            "final_visual_prompt": "...",
            "native_images": [...]
        }
    ]
    """
    slides = []

    for page in pages:
        page_num = page.get("page_number", 1)
        title = page.get("title", "")
        images = page.get("images", [])

        # 推断页面类型（根据标题或页码）
        page_type = _infer_page_type(page_num, title)

        # 处理图片：根据图片模式调整生成策略
        native_images = []
        visual_prompt_parts = []

        for img in images:
            path = img.get("path", "")
            mode = img.get("mode", "INTENT_FUSION")
            role = img.get("role", "")
            position = img.get("position", "center")
            visual_prompt = img.get("final_visual_prompt", img.get("visual_prompt", ""))

            # 跳过占位符
            if path == "PLACEHOLDER":
                continue

            # 根据图片模式构建 native_images
            native_image_entry = _build_native_image_entry(path, mode, role, position)
            if native_image_entry:
                native_images.append(native_image_entry)

            # 收集 visual_prompt
            if visual_prompt:
                visual_prompt_parts.append(visual_prompt)

        # 构建 slide 对象
        slide = {
            "page_num": page_num,
            "type": page_type,
            "final_visual_prompt": "\n\n".join(visual_prompt_parts) if visual_prompt_parts else f"Page {page_num}: {title}",
            "native_images": native_images
        }
        slide["visual_prompt"] = slide["final_visual_prompt"]

        slides.append(slide)

    return slides


def _infer_page_type(page_num: int, title: str) -> str:
    """根据页码和标题推断页面类型"""
    title_lower = title.lower()

    if page_num == 1 or "封面" in title or "cover" in title_lower:
        return "cover"
    elif "章节" in title or "section" in title_lower or title.startswith("第") and "章" in title:
        return "section"
    elif "hero" in title_lower:
        return "hero"
    else:
        return "content"


def _build_native_image_entry(path: str, mode: str, role: str, position: str) -> Optional[Dict[str, Any]]:
    """
    根据图片模式构建 native_image 条目

    三种模式的处理策略：
    1. INTENT_FUSION（意向融合）：只取语义，不保留可识别性
       - integration_mode: blend
       - 不设置 blend_reserved_region，允许完全重绘

    2. ELEMENT_PRESERVE（元素保留）：保留主体，允许重组
       - integration_mode: blend
       - 设置 blend_reserved_region，保留主体区域

    3. ORIGINAL_PRESENT（原图呈现）：保留长宽比，轻微加工
       - integration_mode: blend
       - 设置 blend_reserved_region 为全图，最小化改动
    """
    if not path or path == "PLACEHOLDER":
        return None

    normalized_mode = str(mode or "INTENT_FUSION").upper()
    if normalized_mode not in {"INTENT_FUSION", "ELEMENT_PRESERVE", "ORIGINAL_PRESENT"}:
        normalized_mode = "INTENT_FUSION"

    # 统一使用 blend 模式
    entry = {
        "path": path,
        "integration_mode": "blend",
        "semantic_role": role or "subject",
        "mode": normalized_mode,
    }

    reserved_region = MODE_RESERVED_REGIONS.get(normalized_mode)
    if reserved_region:
        entry["blend_reserved_region"] = dict(reserved_region)

    # 根据 position 调整 bounding_box（用于布局提示）
    entry["bounding_box"] = _position_to_bounding_box(position)

    return entry


def _position_to_bounding_box(position: str) -> Dict[str, float]:
    """将位置描述转换为 bounding_box"""
    return dict(POSITION_BOUNDING_BOXES.get(position, POSITION_BOUNDING_BOXES["center"]))


def _generate_single_slide(slide, visual_plan, slides_dir, generator, resolution, masters, clean_background_image=None, project_dir=None, retry_count=0):
    """
    单页生成逻辑，供串行或并行调用
    masters: dict {'content': img, 'section': img, 'hero': img}
    project_dir: 项目工作目录，用于解析相对路径
    retry_count: 当前重试次数
    """
    page_num = slide['page_num']

    # Check for table data first
    table_data = slide.get('table_data') or slide.get('text_content', {}).get('table_data')
    visualization = slide.get('visualization', '')

    if table_data and visualization in ('bar', 'line', 'pie'):
        try:
            bg_img = clean_background_image if clean_background_image else None
            image = render_chart_image(table_data, visualization, slide.get('style_config', {}), background_image=bg_img)
            slide_path = slides_dir / f"slide_{page_num:02d}.png"
            image.save(slide_path, "PNG")
            return page_num, image
        except Exception as e:
            logger.error(f"Failed to render chart for slide {page_num}: {e}")
            # 分类失败
            failure = classify_failure(e, {
                "page_number": page_num,
                "stage": "chart_rendering",
                "retry_count": retry_count
            })
            raise e

    prompt = slide.get('final_visual_prompt') or slide.get('visual_prompt', '')
    reference_images = []

    # 1. 尝试加载显式指定的模版参考图（支持单张或多张）
    ref_imgs_paths = slide.get('reference_images', [])
    if slide.get('reference_image'):
        if isinstance(slide['reference_image'], list):
            ref_imgs_paths.extend(slide['reference_image'])
        else:
            ref_imgs_paths.append(slide['reference_image'])

    for ref_path in ref_imgs_paths:
        if ref_path and os.path.exists(ref_path):
            try:
                ref_img = Image.open(ref_path)
                reference_images.append(ref_img)
            except Exception as e:
                logger.warning(f"无法加载参考图 {ref_path}: {e}")
                # 分类素材失败
                failure = classify_failure(e, {
                    "page_number": page_num,
                    "image_path": ref_path,
                    "stage": "load_reference",
                    "retry_count": retry_count
                })
                if failure.severity == FailureSeverity.PERMANENT:
                    logger.error(f"素材错误（不可重试）: {failure.error_message}")
                    raise e

    seed_family = _infer_seed_family(slide.get('type'))
    if seed_family in masters and slide.get('seed_role') != 'family_seed' and masters.get(seed_family) is not None:
        try:
            seed_reference = masters[seed_family]
            if hasattr(seed_reference, "copy"):
                seed_reference = seed_reference.copy()
            reference_images.insert(0, seed_reference)
            prompt += (
                f"\n\nCRITICAL INSTRUCTION: An attached {seed_family} seed slide is provided as a VISUAL GRAMMAR reference. "
                "Use it only to inherit palette behavior, typography feel, spacing rhythm, material treatment, and composition discipline. "
                "Do NOT copy or imitate its specific text, subject matter, scene, infographic skeleton, icon cluster, or unique metaphor. "
                "The current slide's approved content and text always override the seed reference."
            )
        except Exception as e:
            logger.warning(f"无法附加 {seed_family} 种子页参考图: {e}")

    is_background_only = slide.get('type') == 'background_only'
    
    raw_native_images = slide.get('native_images', [])
    # Legacy fallback mapping
    if not raw_native_images and slide.get('native_image'):
        raw_native_images = [slide.get('native_image')]

    blend_images = []
    # 统一使用 blend 模式进行图片融合
    for ni in raw_native_images:
        normalized = dict(ni)
        # 强制将所有图片转为 blend
        normalized['integration_mode'] = 'blend'
        if normalized.get("bounding_box") and not normalized.get("blend_reserved_region"):
            normalized["blend_reserved_region"] = dict(normalized["bounding_box"])
        blend_images.append(normalized)

    if blend_images:
        slide["native_images"] = blend_images

    # 把融合图喂给 reference_images
    for bi in blend_images:
        try:
            # Resolve relative paths against project_dir
            img_path = bi['path']
            if not os.path.isabs(img_path):
                # Try project_dir first
                if project_dir:
                    abs_path = os.path.normpath(os.path.join(project_dir, img_path))
                    if os.path.exists(abs_path):
                        img_path = abs_path
            bi_img = Image.open(img_path)
            if bi_img.mode != "RGB":
                bi_img = bi_img.convert("RGB")
            reference_images.append(bi_img)

            # 为重绘设定极强的 Prompt
            role = bi.get('semantic_role', 'subject')
            prompt += f"\n\nCRITICAL INSTRUCTION: We are REDRAWING the provided reference image ({role}). Do NOT just paste it. Seamlessly blend and redraw its essence, data structure, or subject into the background with high-end 3D/UI aesthetics. Ensure perfect color grading and lighting match. Do NOT duplicate or repeat the text/content from the reference image multiple times."
        except Exception as e:
            logger.warning(f"无法加载融合参考图 {bi['path']}: {e}")
            # 分类素材失败
            failure = classify_failure(e, {
                "page_number": page_num,
                "image_path": bi['path'],
                "stage": "load_blend_image",
                "retry_count": retry_count
            })
            if failure.severity == FailureSeverity.PERMANENT:
                logger.error(f"素材错误（不可重试）: {failure.error_message}")
                raise e
    
    image = generator.generate_image(
        prompt, aspect_ratio="16:9",
        reference_images=reference_images,
        is_background_only=is_background_only,
        resolution=resolution,
        native_images=blend_images # 传给 generator 以便生成带有排版意识的 prompt (例如留出左侧空间给重绘)
    )
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

    # 优先使用 slides（当前正式执行结构）
    if isinstance(raw, dict) and "slides" in raw:
        visual_plan = raw.get("slides", [])
        meta = raw.get("meta", {})
    # 支持 pages 结构作为兼容输入
    elif "pages" in raw:
        # 新格式：从 pages 数组转换为旧格式的 slides
        visual_plan = _convert_new_format_to_slides(raw["pages"])
        meta = {"source_file": raw.get("source_file", "")}
    else:
        # 旧格式：兼容现有逻辑
        visual_plan = raw if isinstance(raw, list) else raw.get("slides", raw)
        meta = raw.get("meta", {}) if isinstance(raw, dict) else {}

    for slide in visual_plan:
        if not slide.get("final_visual_prompt") and slide.get("visual_prompt"):
            slide["final_visual_prompt"] = slide["visual_prompt"]

    proj = Path(project_dir) if project_dir else Path(meta.get("project_dir", "output"))
    slides_dir = proj / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    ppt_dir = Path("output") / "ppt"
    
    # 尝试从项目目录推断 ppt_dir（如果是统一的日期格式目录）
    if proj.parent.name == "ppt":
        ppt_dir = proj.parent
    else:
        ppt_dir.mkdir(parents=True, exist_ok=True)
    
    api_key = get_llm_api_key()
    api_base = get_llm_api_base()
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
        missing = [s['page_num'] for s in visual_plan if s['page_num'] not in images_dict]
        if missing:
            print(f"⚠️ 缺少图片: 第 {missing} 页，将跳过或留白")
        date_prefix = date.today().strftime("%Y%m%d")
        
        final_output_name = output_name
        if not final_output_name.startswith(f"{date_prefix}_"):
            final_output_name = f"{date_prefix}_{output_name}"
            
        output_path = proj / f"{final_output_name}.pptx"
        generator.create_advanced_pptx(visual_plan, images_dict, str(output_path), template_path, project_dir=str(proj))
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

            # 种子页重试逻辑
            max_seed_retries = 3
            success = False

            for attempt in range(max_seed_retries):
                try:
                    # Pass current masters state (some might be None, that's expected for seeds)
                    _, img = _generate_single_slide(
                        slide, visual_plan, slides_dir, generator, resolution, masters,
                        clean_background_image, project_dir=str(proj), retry_count=attempt
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
                    success = True
                    break

                except Exception as e:
                    # 分类失败
                    failure = classify_failure(e, {
                        "page_number": slide['page_num'],
                        "stage": "seed",
                        "retry_count": attempt
                    })

                    logger.warning(f"种子页生成失败 (尝试 {attempt+1}/{max_seed_retries}): {failure.error_message}")

                    # 如果是永久性失败，不再重试
                    if failure.severity == FailureSeverity.PERMANENT:
                        logger.error(f"种子页永久性失败，停止重试: {failure.error_message}")
                        break

                    # 暂时性失败，等待后重试
                    if attempt < max_seed_retries - 1:
                        wait_time = 5 * (attempt + 1)  # 递增等待时间
                        logger.info(f"等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)

            if not success:
                logger.error(f"种子页 {slide['page_num']} 最终失败，使用灰色占位图")
                images_dict[slide['page_num']] = Image.new('RGB', (1920, 1080), color='gray')
                indices_to_remove.append(idx)

        # Remove processed seeds from to_run (in reverse order to preserve indices)
        # BUG FIX: Popping from to_run modifies it while we still need to process remaining items.
        # Instead of popping, we just create a new list for remaining items.
        to_run = [s for i, s in enumerate(to_run) if i not in indices_to_remove]

    # Phase 2: 并行生成剩余页
    failures_list: List[FailureReport] = []  # 收集所有失败报告

    def run_one(s):
        pn = s['page_num']
        # Try up to 3 times at the executor level (in addition to generator retries)
        max_exec_attempts = 3
        last_failure = None

        for attempt in range(max_exec_attempts):
            try:
                return _generate_single_slide(
                    s, visual_plan, slides_dir, generator, resolution, masters,
                    clean_background_image, project_dir=str(proj), retry_count=attempt
                )
            except Exception as e:
                # 分类失败
                failure = classify_failure(e, {
                    "page_number": pn,
                    "stage": "parallel",
                    "retry_count": attempt
                })
                last_failure = failure

                logger.warning(f"Page {pn} 尝试 {attempt+1}/{max_exec_attempts} 失败: {failure.error_message}")

                # 如果是永久性失败，不再重试
                if failure.severity == FailureSeverity.PERMANENT:
                    logger.error(f"Page {pn} 永久性失败，停止重试")
                    break

                # 暂时性失败，等待后重试
                if attempt < max_exec_attempts - 1 and failure.can_retry:
                    wait_time = 5 * (attempt + 1)
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

        # 所有重试都失败了
        if last_failure:
            failures_list.append(last_failure)
            logger.error(f"Page {pn} 最终失败: {last_failure.error_message}")

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

    # 打印失败摘要
    if failures_list:
        summary = generate_failure_summary(failures_list)
        print(summary)
        logger.warning(f"生成过程中有 {len(failures_list)} 个失败，详见上方摘要")

    # Get the project name, output name usually already has the date prefix
    # If output_name starts with the date prefix, don't add it again
    date_prefix = date.today().strftime("%Y%m%d")

    final_output_name = output_name
    if not final_output_name.startswith(f"{date_prefix}_"):
        final_output_name = f"{date_prefix}_{output_name}"

    output_path = proj / f"{final_output_name}.pptx"

    # 组装 PPTX
    try:
        generator.create_advanced_pptx(visual_plan, images_dict, str(output_path), template_path, project_dir=str(proj))
        print(f"\n✅ PPT 生成完成: {output_path}")
    except Exception as e:
        # 分类组装失败
        failure = classify_failure(e, {
            "file_path": str(output_path),
            "stage": "assembly"
        })
        logger.error(f"PPT 组装失败: {failure.error_message}")
        failures_list.append(failure)
        print(f"\n❌ PPT 组装失败: {failure.error_message}")
        return None

    return str(output_path)


if __name__ == "__main__":
    pass
