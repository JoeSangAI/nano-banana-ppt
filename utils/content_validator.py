"""
内容一致性校验模块
检查 content_plan.md 和 master_plan.md 的内容一致性
在 execute 前自动检测不一致问题
"""
import re
from pathlib import Path
from typing import List


def validate_content_visual_consistency(project_dir: Path) -> List[str]:
    """
    检查 content_plan.md 和 master_plan.md 的内容一致性

    返回: 问题列表，如果为空则表示一致
    """
    issues = []

    content_plan_path = project_dir / "content_plan.md"
    master_plan_path = project_dir / "master_plan.md"

    if not content_plan_path.exists():
        issues.append("content_plan.md 不存在")
        return issues

    if not master_plan_path.exists():
        issues.append("master_plan.md 不存在")
        return issues

    # 读取文件
    with open(content_plan_path, 'r', encoding='utf-8') as f:
        content_text = f.read()

    with open(master_plan_path, 'r', encoding='utf-8') as f:
        master_text = f.read()

    # 1. 检查页面数量
    content_pages = len(re.findall(r'(?:Slide|第|P)\s*\d+', content_text))
    master_pages = len(re.findall(r'(?:Slide|第|P)\s*\d+', master_text))

    if content_pages != master_pages:
        issues.append(f"页面数量不一致: content_plan有{content_pages}页, master_plan有{master_pages}页")

    # 2. 检查关键数据值（示例：抖音日活）
    # 提取所有数字+单位的模式
    content_numbers = re.findall(r'(\d+\.?\d*)\s*([亿万千百十])', content_text)
    master_numbers = re.findall(r'(\d+\.?\d*)\s*([亿万千百十])', master_text)

    # 检查是否有明显的数据不一致（如 8.3亿 vs 18.3亿）
    content_set = set([f"{num}{unit}" for num, unit in content_numbers])
    master_set = set([f"{num}{unit}" for num, unit in master_numbers])

    # 找出只在一个文件中出现的数据
    only_in_content = content_set - master_set
    only_in_master = master_set - content_set

    if only_in_content or only_in_master:
        issues.append(f"数据不一致: content独有={only_in_content}, master独有={only_in_master}")

    # 3. 检查标题一致性（提取前5个标题对比）
    content_titles = re.findall(r'(?:Slide|第|P)\s*\d+[:：]\s*(.+?)(?=\n|$)', content_text)[:5]
    master_titles = re.findall(r'(?:Slide|第|P)\s*\d+[:：]\s*(.+?)(?=\n|$)', master_text)[:5]

    for i, (ct, mt) in enumerate(zip(content_titles, master_titles)):
        if ct.strip() != mt.strip():
            issues.append(f"第{i+1}页标题不一致: '{ct}' vs '{mt}'")

    return issues
