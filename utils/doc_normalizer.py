"""
文档规范化工具

在用户修改 Markdown 后自动规整格式，检测并报告无法自动修复的问题。
"""

import re
from typing import Tuple, List
from pathlib import Path


def normalize_content_plan(content: str) -> Tuple[str, List[str]]:
    """
    规范化 content_plan.md 的格式

    Args:
        content: 原始 Markdown 内容

    Returns:
        (normalized_content, issues) 元组
        - normalized_content: 规范化后的内容
        - issues: 无法自动修复的问题列表
    """
    issues = []
    lines = content.split('\n')
    normalized_lines = []

    for i, line in enumerate(lines):
        original_line = line

        # 1. 修复标题格式：确保 # 后有空格
        if line.startswith('#'):
            match = re.match(r'^(#+)(\S)', line)
            if match:
                line = match.group(1) + ' ' + line[len(match.group(1)):]

        # 2. 修复图片锚点格式
        if '[IMAGE:' in line or '[image:' in line:
            # 统一大小写
            line = re.sub(r'\[image:', '[IMAGE:', line, flags=re.IGNORECASE)
            # 确保冒号后有空格
            line = re.sub(r'\[IMAGE:(\S)', r'[IMAGE: \1', line)
            # 确保右括号前没有多余空格
            line = re.sub(r'\s+\]', ']', line)

            # 检查是否缺少语义锚点
            if re.search(r'\[IMAGE:\s*\]', line):
                issues.append(f"第 {i+1} 行：图片锚点缺少语义描述")

        # 3. 修复中英文标点混用
        # 中文内容使用中文标点
        if re.search(r'[\u4e00-\u9fff]', line):
            line = line.replace(',', '，').replace(';', '；')
            # 但保留代码、链接、锚点中的英文标点
            line = re.sub(r'(\[IMAGE：)', '[IMAGE:', line)

        # 4. 修复多余空行（连续超过 2 个空行压缩为 2 个）
        if line.strip() == '':
            if len(normalized_lines) >= 2 and \
               normalized_lines[-1].strip() == '' and \
               normalized_lines[-2].strip() == '':
                continue  # 跳过第三个及以后的空行

        # 5. 修复行尾空格
        line = line.rstrip()

        normalized_lines.append(line)

    # 6. 确保文件以单个换行符结尾
    while normalized_lines and normalized_lines[-1].strip() == '':
        normalized_lines.pop()

    normalized_content = '\n'.join(normalized_lines) + '\n'

    # 7. 检查必要的结构
    if not re.search(r'^#\s+', normalized_content, re.MULTILINE):
        issues.append("缺少标题（应至少有一个 # 标题）")

    return normalized_content, issues


def normalize_visual_plan(content: str) -> Tuple[str, List[str]]:
    """
    规范化 visual_plan.md 的格式

    Args:
        content: 原始 Markdown 内容

    Returns:
        (normalized_content, issues) 元组
    """
    issues = []
    lines = content.split('\n')
    normalized_lines = []

    in_image_block = False
    image_block_start = 0

    for i, line in enumerate(lines):
        original_line = line

        # 1. 修复标题格式
        if line.startswith('#'):
            match = re.match(r'^(#+)(\S)', line)
            if match:
                line = match.group(1) + ' ' + line[len(match.group(1)):]

        # 2. 检测图片块
        if line.strip().startswith('```image'):
            in_image_block = True
            image_block_start = i + 1
        elif line.strip() == '```' and in_image_block:
            in_image_block = False

        # 3. 检查图片块内的字段
        if in_image_block and ':' in line:
            field_match = re.match(r'^\s*(\w+):\s*(.*)$', line)
            if field_match:
                field_name = field_match.group(1)
                field_value = field_match.group(2).strip()

                # 检查必填字段
                if field_name == 'path' and not field_value:
                    issues.append(f"第 {i+1} 行：图片路径不能为空")
                elif field_name == 'mode' and field_value not in ['INTENT_FUSION', 'ELEMENT_PRESERVE', 'ORIGINAL_PRESENT', '']:
                    issues.append(f"第 {i+1} 行：图片模式非法（应为 INTENT_FUSION/ELEMENT_PRESERVE/ORIGINAL_PRESENT）")

        # 4. 修复行尾空格
        line = line.rstrip()

        normalized_lines.append(line)

    # 5. 确保文件以单个换行符结尾
    while normalized_lines and normalized_lines[-1].strip() == '':
        normalized_lines.pop()

    normalized_content = '\n'.join(normalized_lines) + '\n'

    return normalized_content, issues


def normalize_brief(content: str) -> Tuple[str, List[str]]:
    """
    规范化 brief.md 的格式

    Args:
        content: 原始 Markdown 内容

    Returns:
        (normalized_content, issues) 元组
    """
    issues = []

    # 检查 YAML frontmatter
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
    if not frontmatter_match:
        issues.append("缺少 YAML frontmatter（应以 --- 开始和结束）")
        return content, issues

    yaml_content = frontmatter_match.group(1)
    body_content = frontmatter_match.group(2)

    # 检查必填字段
    if 'goal:' not in yaml_content:
        issues.append("YAML frontmatter 缺少必填字段：goal")

    # 规范化 body
    body_lines = body_content.split('\n')
    normalized_body_lines = []

    for line in body_lines:
        # 修复行尾空格
        line = line.rstrip()
        normalized_body_lines.append(line)

    # 确保文件以单个换行符结尾
    while normalized_body_lines and normalized_body_lines[-1].strip() == '':
        normalized_body_lines.pop()

    normalized_content = f"---\n{yaml_content}\n---\n" + '\n'.join(normalized_body_lines) + '\n'

    return normalized_content, issues
