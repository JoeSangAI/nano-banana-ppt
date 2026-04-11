"""
文档规范化工具

在用户修改 Markdown 后自动规整格式，检测并报告无法自动修复的问题。

图片块格式示例：
```image
path: output/images/product_screenshot.png
mode: ELEMENT_PRESERVE
role: 展示产品核心功能
position: center
```

支持的字段：
- path: 图片路径（必填，可以是 "PLACEHOLDER" 表示待补图）
- mode: 图片模式（必填，INTENT_FUSION/ELEMENT_PRESERVE/ORIGINAL_PRESENT）
- role: 图片在页面中的作用（可选）
- position: 图片位置（可选，center/left/right/full）
"""

import re
from typing import Tuple, List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ImageBlock:
    """图片块数据结构"""
    path: str
    mode: str
    role: Optional[str] = None
    position: Optional[str] = None
    line_number: int = 0  # 在文档中的行号，用于错误报告

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = [
            "```image",
            f"path: {self.path}",
            f"mode: {self.mode}"
        ]
        if self.role:
            lines.append(f"role: {self.role}")
        if self.position:
            lines.append(f"position: {self.position}")
        lines.append("```")
        return '\n'.join(lines)


def parse_image_blocks(content: str) -> Tuple[List[ImageBlock], List[str]]:
    """
    解析 visual_plan.md 中的图片块

    Args:
        content: Markdown 内容

    Returns:
        (image_blocks, issues) 元组
        - image_blocks: 解析出的图片块列表
        - issues: 解析过程中发现的问题
    """
    issues = []
    image_blocks = []
    lines = content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 检测图片块开始
        if line.startswith('```image'):
            block_start = i
            block_data = {}
            i += 1

            # 解析图片块内容
            while i < len(lines):
                line = lines[i].strip()

                # 图片块结束
                if line == '```':
                    # 验证必填字段
                    if 'path' not in block_data:
                        issues.append(f"第 {block_start+1} 行：图片块缺少必填字段 path")
                    if 'mode' not in block_data:
                        issues.append(f"第 {block_start+1} 行：图片块缺少必填字段 mode")
                    else:
                        # 验证 mode 值
                        valid_modes = ['INTENT_FUSION', 'ELEMENT_PRESERVE', 'ORIGINAL_PRESENT']
                        if block_data['mode'] not in valid_modes:
                            issues.append(f"第 {block_start+1} 行：图片模式非法（应为 {'/'.join(valid_modes)}）")

                    # 创建 ImageBlock 对象
                    if 'path' in block_data and 'mode' in block_data:
                        image_block = ImageBlock(
                            path=block_data['path'],
                            mode=block_data['mode'],
                            role=block_data.get('role'),
                            position=block_data.get('position'),
                            line_number=block_start + 1
                        )
                        image_blocks.append(image_block)

                    break

                # 解析字段
                if ':' in line:
                    field_match = re.match(r'^(\w+):\s*(.*)$', line)
                    if field_match:
                        field_name = field_match.group(1)
                        field_value = field_match.group(2).strip()

                        # 验证字段名
                        valid_fields = ['path', 'mode', 'role', 'position']
                        if field_name not in valid_fields:
                            issues.append(f"第 {i+1} 行：未知字段 {field_name}（有效字段：{', '.join(valid_fields)}）")
                        else:
                            block_data[field_name] = field_value

                i += 1

        i += 1

    return image_blocks, issues


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

    支持：
    - 一页多图：同一个标题下可以有多个图片块
    - 待补图占位：path 可以是 "PLACEHOLDER"

    Args:
        content: 原始 Markdown 内容

    Returns:
        (normalized_content, issues) 元组
    """
    issues = []

    # 先用解析函数检查图片块
    image_blocks, parse_issues = parse_image_blocks(content)
    issues.extend(parse_issues)

    # 统计每页的图片数量
    lines = content.split('\n')
    current_slide_title = None
    slide_image_counts = {}

    for i, line in enumerate(lines):
        # 检测幻灯片标题（## 开头）
        if re.match(r'^##\s+', line):
            current_slide_title = line.strip()
            if current_slide_title not in slide_image_counts:
                slide_image_counts[current_slide_title] = 0

        # 检测图片块
        if line.strip().startswith('```image') and current_slide_title:
            slide_image_counts[current_slide_title] += 1

    # 检查待补图占位
    placeholder_count = sum(1 for block in image_blocks if block.path == 'PLACEHOLDER')
    if placeholder_count > 0:
        issues.append(f"发现 {placeholder_count} 个待补图占位（path: PLACEHOLDER），执行前需要补充实际图片")

    # 格式规范化
    normalized_lines = []

    for i, line in enumerate(lines):
        # 1. 修复标题格式
        if line.startswith('#'):
            match = re.match(r'^(#+)(\S)', line)
            if match:
                line = match.group(1) + ' ' + line[len(match.group(1)):]

        # 2. 修复行尾空格
        line = line.rstrip()

        normalized_lines.append(line)

    # 3. 确保文件以单个换行符结尾
    while normalized_lines and normalized_lines[-1].strip() == '':
        normalized_lines.pop()

    normalized_content = '\n'.join(normalized_lines) + '\n'

    # 4. 报告一页多图的情况（信息性，不是错误）
    multi_image_slides = {title: count for title, count in slide_image_counts.items() if count > 1}
    if multi_image_slides:
        for title, count in multi_image_slides.items():
            issues.append(f"信息：{title} 包含 {count} 张图片（一页多图）")

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
