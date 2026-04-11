"""
Content Plan Compiler - 将 content_plan.md 编译为 content_plan.json

将用户确认的 Markdown 格式内容计划编译为机器可执行的 JSON 格式。
"""

import re
import json
from typing import List, Dict, Any
from pathlib import Path


def compile_content_plan(md_path: str, json_path: str = None) -> Dict[str, Any]:
    """
    将 content_plan.md 编译为 content_plan.json

    Args:
        md_path: content_plan.md 文件路径
        json_path: 输出的 JSON 文件路径（可选，默认为同目录下的 content_plan.json）

    Returns:
        编译后的 JSON 数据结构
    """
    md_path = Path(md_path)
    if not md_path.exists():
        raise FileNotFoundError(f"Content plan not found: {md_path}")

    # 读取 Markdown 内容
    content = md_path.read_text(encoding='utf-8')

    # 解析结构
    slides = _parse_markdown_structure(content)

    # 构建 JSON 结构
    result = {
        "slides": slides,
        "total_slides": len(slides),
        "source_file": str(md_path)
    }

    # 保存 JSON
    if json_path is None:
        json_path = md_path.parent / "content_plan.json"
    else:
        json_path = Path(json_path)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    return result


def _parse_markdown_structure(content: str) -> List[Dict[str, Any]]:
    """
    解析 Markdown 结构，提取幻灯片信息

    返回格式：
    [
        {
            "slide_number": 1,
            "type": "cover",
            "title": "标题",
            "content": "内容段落",
            "image_anchors": ["语义锚点1", "语义锚点2"]
        },
        ...
    ]
    """
    slides = []
    lines = content.split('\n')

    current_slide = None
    current_content_lines = []
    slide_number = 0

    for line in lines:
        # 检测标题（# 或 ##）
        title_match = re.match(r'^(#{1,2})\s+(.+)$', line)
        if title_match:
            # 保存上一张幻灯片
            if current_slide:
                current_slide['content'] = '\n'.join(current_content_lines).strip()
                slides.append(current_slide)
                current_content_lines = []

            # 开始新幻灯片
            slide_number += 1
            level = len(title_match.group(1))
            title = title_match.group(2).strip()

            # 判断幻灯片类型
            slide_type = _infer_slide_type(title, slide_number, level)

            current_slide = {
                "slide_number": slide_number,
                "type": slide_type,
                "title": title,
                "content": "",
                "image_anchors": []
            }
            continue

        # 检测图片锚点标记 [IMAGE: xxx]
        image_anchor_match = re.match(r'^\[IMAGE:\s*(.+?)\]$', line.strip())
        if image_anchor_match and current_slide:
            anchor = image_anchor_match.group(1).strip()
            current_slide['image_anchors'].append(anchor)
            continue

        # 普通内容行
        if current_slide and line.strip():
            current_content_lines.append(line)

    # 保存最后一张幻灯片
    if current_slide:
        current_slide['content'] = '\n'.join(current_content_lines).strip()
        slides.append(current_slide)

    return slides


def _infer_slide_type(title: str, slide_number: int, level: int) -> str:
    """
    推断幻灯片类型

    类型：
    - cover: 封面页
    - section: 章节页
    - content: 内容页
    - quote: 引用页
    - data: 数据页
    """
    title_lower = title.lower()

    # 第一页通常是封面
    if slide_number == 1:
        return "cover"

    # 一级标题通常是章节页
    if level == 1:
        return "section"

    # 根据关键词判断
    if any(keyword in title_lower for keyword in ['数据', 'data', '图表', 'chart', '统计']):
        return "data"

    if any(keyword in title_lower for keyword in ['引用', 'quote', '名言']):
        return "quote"

    # 默认为内容页
    return "content"


if __name__ == "__main__":
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        md_file = sys.argv[1]
        result = compile_content_plan(md_file)
        print(f"✓ 编译完成：{result['total_slides']} 张幻灯片")
        print(f"✓ 输出文件：{Path(md_file).parent / 'content_plan.json'}")
