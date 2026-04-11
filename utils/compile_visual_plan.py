"""
Visual Plan Compiler - 将 visual_plan.md 编译为 visual_plan.json

将用户确认的 Markdown 格式视觉计划编译为机器可执行的 JSON 格式。
根据图片模式生成不同的 prompt 策略。
"""

import re
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from .doc_normalizer import parse_image_blocks, ImageBlock


def compile_visual_plan(md_path: str, json_path: str = None) -> Dict[str, Any]:
    """
    将 visual_plan.md 编译为 visual_plan.json

    Args:
        md_path: visual_plan.md 文件路径
        json_path: 输出的 JSON 文件路径（可选，默认为同目录下的 visual_plan.json）

    Returns:
        编译后的 JSON 数据结构
    """
    md_path = Path(md_path)
    if not md_path.exists():
        raise FileNotFoundError(f"Visual plan not found: {md_path}")

    # 读取 Markdown 内容
    content = md_path.read_text(encoding='utf-8')

    # 解析结构
    pages = _parse_visual_plan_structure(content)

    # 构建 JSON 结构
    result = {
        "pages": pages,
        "total_pages": len(pages),
        "source_file": str(md_path)
    }

    # 保存 JSON
    if json_path is None:
        json_path = md_path.parent / "visual_plan.json"
    else:
        json_path = Path(json_path)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    return result


def _parse_visual_plan_structure(content: str) -> List[Dict[str, Any]]:
    """
    解析 visual_plan.md 结构，提取页面和图片块信息

    返回格式：
    [
        {
            "page_number": 1,
            "title": "第 1 页 · 标题",
            "images": [
                {
                    "path": "output/images/xxx.png",
                    "mode": "INTENT_FUSION",
                    "role": "图片作用",
                    "position": "center",
                    "visual_prompt": "生成的完整 prompt"
                }
            ]
        },
        ...
    ]
    """
    pages = []
    lines = content.split('\n')

    current_page = None
    current_page_content = []
    in_image_block = False
    current_image_block_lines = []

    for i, line in enumerate(lines):
        # 检测页面标题（## 开头）
        page_title_match = re.match(r'^##\s+(.+)$', line)
        if page_title_match:
            # 保存上一个页面
            if current_page:
                pages.append(current_page)

            # 开始新页面
            title = page_title_match.group(1).strip()

            # 尝试提取页面编号
            page_num_match = re.match(r'第\s*(\d+)\s*页', title)
            page_number = int(page_num_match.group(1)) if page_num_match else len(pages) + 1

            current_page = {
                "page_number": page_number,
                "title": title,
                "images": []
            }
            current_page_content = []
            continue

        # 检测图片块开始
        if line.strip() == '```image':
            in_image_block = True
            current_image_block_lines = []
            continue

        # 检测图片块结束
        if in_image_block and line.strip() == '```':
            in_image_block = False
            # 解析图片块
            image_block_content = '\n'.join(['```image'] + current_image_block_lines + ['```'])
            image_blocks, issues = parse_image_blocks(image_block_content)

            if image_blocks and current_page:
                image_block = image_blocks[0]
                # 生成 visual_prompt
                visual_prompt = _generate_visual_prompt(image_block, current_page)

                current_page['images'].append({
                    "path": image_block.path,
                    "mode": image_block.mode,
                    "role": image_block.role,
                    "position": image_block.position,
                    "visual_prompt": visual_prompt
                })

            current_image_block_lines = []
            continue

        # 收集图片块内容
        if in_image_block:
            current_image_block_lines.append(line)
            continue

        # 收集页面内容（用于生成 prompt 的上下文）
        if current_page and line.strip() and not line.strip().startswith('---'):
            current_page_content.append(line.strip())

    # 保存最后一个页面
    if current_page:
        pages.append(current_page)

    return pages


def _generate_visual_prompt(image_block: ImageBlock, page_context: Dict[str, Any]) -> str:
    """
    根据图片模式生成 visual_prompt

    三种模式的 prompt 策略：
    1. INTENT_FUSION（意向融合）：只取语义，不保留可识别性
       - 提取图片的情感、氛围、色调
       - 不要求保留具体元素
       - 允许完全重新创作

    2. ELEMENT_PRESERVE（元素保留）：保留主体，允许重组
       - 保留图片中的关键元素（人物、产品、图标等）
       - 允许改变背景、布局、风格
       - 保持元素的可识别性

    3. ORIGINAL_PRESENT（原图呈现）：保留长宽比，轻微加工
       - 尽可能保留原图
       - 只做轻微的裁剪、调色、滤镜
       - 保持原图的完整性

    Args:
        image_block: 图片块对象
        page_context: 页面上下文信息

    Returns:
        生成的 visual_prompt
    """
    mode = image_block.mode
    role = image_block.role or "装饰图片"
    position = image_block.position or "center"
    page_title = page_context.get('title', '')

    # 基础上下文
    base_context = f"页面标题：{page_title}\n图片作用：{role}\n图片位置：{position}"

    if mode == "INTENT_FUSION":
        # 意向融合：只取语义，完全重新创作
        prompt = f"""【意向融合模式】
{base_context}

创作要求：
- 根据图片的情感、氛围、色调进行创作
- 不需要保留原图的具体元素
- 可以完全重新设计构图和内容
- 确保与页面主题和作用相符

参考图片路径：{image_block.path}
（仅作为情感和氛围参考，不要求保留具体内容）
"""

    elif mode == "ELEMENT_PRESERVE":
        # 元素保留：保留主体，允许重组
        prompt = f"""【元素保留模式】
{base_context}

创作要求：
- 识别并保留图片中的关键元素（人物、产品、图标、文字等）
- 可以改变背景、布局、配色、风格
- 保持关键元素的可识别性和完整性
- 允许重新排列和组合元素

参考图片路径：{image_block.path}
（保留图中的主要元素，但可以重新设计背景和布局）
"""

    elif mode == "ORIGINAL_PRESENT":
        # 原图呈现：保留长宽比，轻微加工
        prompt = f"""【原图呈现模式】
{base_context}

创作要求：
- 尽可能保留原图的完整性
- 保持原图的长宽比
- 只做必要的裁剪、调色、滤镜处理
- 确保图片清晰度和视觉质量
- 可以添加轻微的边框、阴影等装饰效果

参考图片路径：{image_block.path}
（尽量保持原图，只做轻微优化）
"""

    else:
        # 未知模式，使用默认策略
        prompt = f"""【默认模式】
{base_context}

参考图片路径：{image_block.path}
"""

    return prompt.strip()


if __name__ == "__main__":
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        md_file = sys.argv[1]
        result = compile_visual_plan(md_file)
        print(f"✓ 编译完成：{result['total_pages']} 个页面")

        # 统计图片数量
        total_images = sum(len(page['images']) for page in result['pages'])
        print(f"✓ 图片总数：{total_images} 张")

        # 统计待补图数量
        placeholder_count = sum(
            1 for page in result['pages']
            for img in page['images']
            if img['path'] == 'PLACEHOLDER'
        )
        if placeholder_count > 0:
            print(f"⚠ 待补图：{placeholder_count} 张")

        print(f"✓ 输出文件：{Path(md_file).parent / 'visual_plan.json'}")
