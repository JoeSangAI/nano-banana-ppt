"""
Plan Sync - 计划文件同步工具

在局部修改生效后，将 JSON 的变更同步回 Markdown 文件，确保两者保持一致。
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def sync_content_plan(
    json_path: str,
    md_path: str = None,
    record_history: bool = True
) -> Dict[str, Any]:
    """
    将 content_plan.json 的修改同步回 content_plan.md

    Args:
        json_path: content_plan.json 文件路径
        md_path: content_plan.md 文件路径（可选，默认为同目录下的 content_plan.md）
        record_history: 是否记录修改历史

    Returns:
        同步结果，包含：
        - success: 是否成功
        - message: 结果消息
        - changes: 变更摘要
    """
    json_path = Path(json_path)
    if not json_path.exists():
        return {
            "success": False,
            "message": f"JSON 文件不存在: {json_path}",
            "changes": []
        }

    # 确定 Markdown 文件路径
    if md_path is None:
        md_path = json_path.parent / "content_plan.md"
    else:
        md_path = Path(md_path)

    try:
        # 读取 JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            content_plan = json.load(f)

        # 读取现有 Markdown（如果存在）
        old_md_content = ""
        if md_path.exists():
            old_md_content = md_path.read_text(encoding='utf-8')

        # 生成新的 Markdown
        new_md_content = _generate_content_plan_markdown(content_plan)

        # 检测变更
        changes = _detect_content_changes(old_md_content, new_md_content)

        # 写入 Markdown
        md_path.write_text(new_md_content, encoding='utf-8')

        # 记录修改历史
        if record_history and changes:
            _record_modification_history(
                md_path.parent,
                "content_plan",
                changes
            )

        return {
            "success": True,
            "message": f"同步完成: {len(changes)} 处变更",
            "changes": changes
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"同步失败: {e}",
            "changes": []
        }


def sync_visual_plan(
    json_path: str,
    md_path: str = None,
    record_history: bool = True
) -> Dict[str, Any]:
    """
    将 visual_plan.json 的修改同步回 visual_plan.md

    Args:
        json_path: visual_plan.json 文件路径
        md_path: visual_plan.md 文件路径（可选，默认为同目录下的 visual_plan.md）
        record_history: 是否记录修改历史

    Returns:
        同步结果，包含：
        - success: 是否成功
        - message: 结果消息
        - changes: 变更摘要
    """
    json_path = Path(json_path)
    if not json_path.exists():
        return {
            "success": False,
            "message": f"JSON 文件不存在: {json_path}",
            "changes": []
        }

    # 确定 Markdown 文件路径
    if md_path is None:
        md_path = json_path.parent / "visual_plan.md"
    else:
        md_path = Path(md_path)

    try:
        # 读取 JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            visual_plan = json.load(f)

        # 读取现有 Markdown（如果存在）
        old_md_content = ""
        if md_path.exists():
            old_md_content = md_path.read_text(encoding='utf-8')

        # 生成新的 Markdown
        new_md_content = _generate_visual_plan_markdown(visual_plan)

        # 检测变更
        changes = _detect_visual_changes(old_md_content, new_md_content)

        # 写入 Markdown
        md_path.write_text(new_md_content, encoding='utf-8')

        # 记录修改历史
        if record_history and changes:
            _record_modification_history(
                md_path.parent,
                "visual_plan",
                changes
            )

        return {
            "success": True,
            "message": f"同步完成: {len(changes)} 处变更",
            "changes": changes
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"同步失败: {e}",
            "changes": []
        }


def _generate_content_plan_markdown(content_plan: Dict[str, Any]) -> str:
    """
    从 JSON 生成 content_plan.md 的 Markdown 内容

    Args:
        content_plan: content_plan.json 的数据结构

    Returns:
        Markdown 格式的内容
    """
    lines = []

    # 添加文件头
    lines.append("# Content Plan")
    lines.append("")
    lines.append(f"总页数: {content_plan.get('total_slides', 0)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 遍历每张幻灯片
    for slide in content_plan.get("slides", []):
        slide_number = slide.get("slide_number", 0)
        slide_type = slide.get("type", "content")
        title = slide.get("title", "")
        content = slide.get("content", "")
        image_anchors = slide.get("image_anchors", [])

        # 根据类型决定标题级别
        if slide_type == "cover" or slide_number == 1:
            lines.append(f"# {title}")
        elif slide_type == "section":
            lines.append(f"# {title}")
        else:
            lines.append(f"## {title}")

        lines.append("")

        # 添加内容
        if content:
            lines.append(content)
            lines.append("")

        # 添加图片锚点
        for anchor in image_anchors:
            lines.append(f"[IMAGE: {anchor}]")

        if image_anchors:
            lines.append("")

        lines.append("---")
        lines.append("")

    return '\n'.join(lines)


def _generate_visual_plan_markdown(visual_plan: Dict[str, Any]) -> str:
    """
    从 JSON 生成 visual_plan.md 的 Markdown 内容

    Args:
        visual_plan: visual_plan.json 的数据结构

    Returns:
        Markdown 格式的内容
    """
    lines = []

    # 添加文件头
    lines.append("# Visual Plan")
    lines.append("")
    lines.append(f"总页数: {visual_plan.get('total_pages', 0)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 遍历每个页面
    for page in visual_plan.get("pages", []):
        page_number = page.get("page_number", 0)
        title = page.get("title", f"第 {page_number} 页")
        images = page.get("images", [])

        # 页面标题
        lines.append(f"## {title}")
        lines.append("")

        # 遍历图片
        for img in images:
            path = img.get("path", "PLACEHOLDER")
            mode = img.get("mode", "INTENT_FUSION")
            role = img.get("role", "")
            position = img.get("position", "center")

            # 图片块
            lines.append("```image")
            lines.append(f"path: {path}")
            lines.append(f"mode: {mode}")
            lines.append(f"role: {role}")
            lines.append(f"position: {position}")
            lines.append("```")
            lines.append("")

        lines.append("---")
        lines.append("")

    return '\n'.join(lines)


def _detect_content_changes(old_content: str, new_content: str) -> List[str]:
    """
    检测 content_plan 的变更

    Args:
        old_content: 旧的 Markdown 内容
        new_content: 新的 Markdown 内容

    Returns:
        变更摘要列表
    """
    changes = []

    # 简单的行级对比
    old_lines = old_content.split('\n') if old_content else []
    new_lines = new_content.split('\n')

    # 提取标题行进行对比
    old_titles = [line for line in old_lines if line.startswith('#')]
    new_titles = [line for line in new_lines if line.startswith('#')]

    # 检测新增的标题
    for title in new_titles:
        if title not in old_titles:
            changes.append(f"新增页面: {title}")

    # 检测删除的标题
    for title in old_titles:
        if title not in new_titles:
            changes.append(f"删除页面: {title}")

    # 检测内容变化
    if len(old_lines) != len(new_lines):
        changes.append(f"内容行数变化: {len(old_lines)} -> {len(new_lines)}")

    return changes


def _detect_visual_changes(old_content: str, new_content: str) -> List[str]:
    """
    检测 visual_plan 的变更

    Args:
        old_content: 旧的 Markdown 内容
        new_content: 新的 Markdown 内容

    Returns:
        变更摘要列表
    """
    changes = []

    # 简单的行级对比
    old_lines = old_content.split('\n') if old_content else []
    new_lines = new_content.split('\n')

    # 提取页面标题
    old_pages = [line for line in old_lines if line.startswith('## 第')]
    new_pages = [line for line in new_lines if line.startswith('## 第')]

    # 检测页面变化
    if len(old_pages) != len(new_pages):
        changes.append(f"页面数量变化: {len(old_pages)} -> {len(new_pages)}")

    # 提取图片块
    old_image_blocks = old_content.count('```image')
    new_image_blocks = new_content.count('```image')

    # 检测图片变化
    if old_image_blocks != new_image_blocks:
        changes.append(f"图片数量变化: {old_image_blocks} -> {new_image_blocks}")

    return changes


def _record_modification_history(
    project_dir: Path,
    plan_type: str,
    changes: List[str]
) -> None:
    """
    记录修改历史

    Args:
        project_dir: 项目目录
        plan_type: 计划类型（content_plan 或 visual_plan）
        changes: 变更摘要列表
    """
    history_file = project_dir / "modification_history.log"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"\n[{timestamp}] {plan_type} 同步\n"

    for change in changes:
        log_entry += f"  - {change}\n"

    # 追加到历史文件
    with open(history_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        json_path = Path(json_file)

        if "content_plan" in json_file:
            result = sync_content_plan(json_file)
        elif "visual_plan" in json_file:
            result = sync_visual_plan(json_file)
        else:
            print("❌ 无法识别计划类型，文件名应包含 'content_plan' 或 'visual_plan'")
            sys.exit(1)

        if result["success"]:
            print(f"✓ {result['message']}")
            if result["changes"]:
                print("\n变更摘要:")
                for change in result["changes"]:
                    print(f"  - {change}")
        else:
            print(f"✗ {result['message']}")
            sys.exit(1)
