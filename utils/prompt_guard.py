"""
Prompt Guard - Visual Prompt 质量审查工具

将 ReviewerAgent 降级为工具函数，实现分层审查策略：
- 全量轻检查：快速扫描所有页面，识别明显问题
- 种子页深查：对种子页进行深度审查
- 异常页必查：对检测到问题的页面进行深度审查
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json

from .provider_config import DEFAULT_LLM_MODEL
from .prompt_spec import format_prompt_sections

logger = logging.getLogger(__name__)
VALID_IMAGE_MODES = ("INTENT_FUSION", "ELEMENT_PRESERVE", "ORIGINAL_PRESENT")


class CheckIssue:
    """审查问题"""
    def __init__(
        self,
        page_number: int,
        severity: str,  # "error", "warning", "info"
        category: str,  # "style", "content", "technical", "narrative", "redundancy", "emotion"
        message: str,
        suggestion: str = ""
    ):
        self.page_number = page_number
        self.severity = severity
        self.category = category
        self.message = message
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion
        }


class ReviewReport:
    """审查报告"""
    def __init__(self):
        self.issues: List[CheckIssue] = []
        self.patches: Dict[str, str] = {}  # "{page_number}:{image_index}" -> improved_prompt
        self.stats = {
            "total_pages": 0,
            "checked_pages": 0,
            "light_checked": 0,
            "deep_checked": 0,
            "errors": 0,
            "warnings": 0,
            "infos": 0
        }

    def add_issue(self, issue: CheckIssue):
        """添加问题"""
        self.issues.append(issue)
        if issue.severity == "error":
            self.stats["errors"] += 1
        elif issue.severity == "warning":
            self.stats["warnings"] += 1
        else:
            self.stats["infos"] += 1

    def add_patch(self, page_number: int, image_index: int, improved_prompt: str):
        """添加改进后的 prompt"""
        self.patches[f"{page_number}:{image_index}"] = improved_prompt

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issues": [issue.to_dict() for issue in self.issues],
            "patches": self.patches,
            "stats": self.stats
        }


def review_visual_plan(
    visual_plan_json_path: str,
    llm_client,
    strategy: str = "auto",  # "auto", "light", "deep", "seed_only"
    seed_pages: List[int] = None,
    content_plan_json_path: str = None,
    style_config: Dict[str, Any] = None
) -> ReviewReport:
    """
    审查 visual_plan.json 中的所有 visual prompts

    Args:
        visual_plan_json_path: visual_plan.json 文件路径
        llm_client: LLM 客户端
        strategy: 审查策略
            - "auto": 自动选择（全量轻检查 + 种子页深查 + 异常页必查）
            - "light": 仅轻量检查
            - "deep": 全量深度检查
            - "seed_only": 仅检查种子页
        seed_pages: 种子页列表（页码）
        content_plan_json_path: content_plan.json 路径（可选，用于内容一致性检查）
        style_config: 风格配置（可选）

    Returns:
        ReviewReport 对象，包含问题列表和改进建议
    """
    # 读取 visual_plan.json
    visual_plan_path = Path(visual_plan_json_path)
    if not visual_plan_path.exists():
        raise FileNotFoundError(f"Visual plan not found: {visual_plan_path}")

    with open(visual_plan_path, 'r', encoding='utf-8') as f:
        visual_plan = json.load(f)

    pages = visual_plan.get('pages', [])
    report = ReviewReport()
    report.stats['total_pages'] = len(pages)

    # 读取 content_plan（如果提供）
    content_plan = None
    if content_plan_json_path:
        content_plan_path = Path(content_plan_json_path)
        if content_plan_path.exists():
            with open(content_plan_path, 'r', encoding='utf-8') as f:
                content_plan = json.load(f)

    # 第一阶段：全量轻检查（除非策略是 seed_only）
    if strategy != "seed_only":
        logger.info("🔍 第一阶段：全量轻检查...")
        for page in pages:
            page_num = page.get('page_number', 0)
            issues = _light_check_page(page, content_plan, style_config)
            for issue in issues:
                report.add_issue(issue)
            report.stats['light_checked'] += 1

    # 识别需要深度检查的页面
    pages_to_deep_check = set()

    # 添加种子页
    if seed_pages:
        pages_to_deep_check.update(seed_pages)

    # 添加异常页（轻检查中发现 error 或 warning 的页面）
    if strategy == "auto":
        for issue in report.issues:
            if issue.severity in ["error", "warning"]:
                pages_to_deep_check.add(issue.page_number)

    # 如果策略是 deep，检查所有页面
    if strategy == "deep":
        pages_to_deep_check = set(page.get('page_number', 0) for page in pages)

    # 第二阶段：深度检查
    if pages_to_deep_check:
        logger.info(f"🔍 第二阶段：深度检查 {len(pages_to_deep_check)} 个页面...")
        for page in pages:
            page_num = page.get('page_number', 0)
            if page_num in pages_to_deep_check:
                issues, improved_prompts = _deep_check_page(
                    page, llm_client, content_plan, style_config
                )
                for issue in issues:
                    report.add_issue(issue)
                for img_idx, improved_prompt in improved_prompts.items():
                    report.add_patch(page_num, img_idx, improved_prompt)
                report.stats['deep_checked'] += 1

    report.stats['checked_pages'] = report.stats['light_checked'] + report.stats['deep_checked']

    logger.info(f"✅ 审查完成：{report.stats['checked_pages']} 页，"
                f"{report.stats['errors']} 错误，"
                f"{report.stats['warnings']} 警告，"
                f"{report.stats['infos']} 提示")

    return report


def _light_check_page(
    page: Dict[str, Any],
    content_plan: Optional[Dict[str, Any]],
    style_config: Optional[Dict[str, Any]]
) -> List[CheckIssue]:
    """
    轻量检查单个页面（快速扫描，不调用 LLM）

    检查项：
    1. 图片路径是否为 PLACEHOLDER
    2. visual_prompt 是否为空
    3. mode 是否合法
    4. 是否有明显的格式问题
    """
    issues = []
    page_num = page.get('page_number', 0)
    images = page.get('images', [])

    # 检查是否有图片
    if not images:
        issues.append(CheckIssue(
            page_number=page_num,
            severity="warning",
            category="content",
            message="页面没有图片",
            suggestion="考虑添加至少一张图片以增强视觉效果"
        ))

    for img_idx, img in enumerate(images):
        # 检查 PLACEHOLDER
        if img.get('path') == 'PLACEHOLDER':
            issues.append(CheckIssue(
                page_number=page_num,
                severity="error",
                category="content",
                message=f"图片 {img_idx + 1} 仍为占位符",
                suggestion="需要补充实际图片路径"
            ))

        # 检查 final_visual_prompt 是否为空（兼容旧字段 visual_prompt）
        visual_prompt = (img.get('final_visual_prompt') or img.get('visual_prompt', '')).strip()
        if not visual_prompt:
            issues.append(CheckIssue(
                page_number=page_num,
                severity="error",
                category="content",
                message=f"图片 {img_idx + 1} 的 visual_prompt 为空",
                suggestion="需要生成 visual_prompt"
            ))

        # 检查 mode 是否合法
        mode = img.get('mode', '')
        if mode not in VALID_IMAGE_MODES:
            issues.append(CheckIssue(
                page_number=page_num,
                severity="error",
                category="technical",
                message=f"图片 {img_idx + 1} 的 mode 不合法：{mode}",
                suggestion=f"mode 必须是以下之一：{', '.join(VALID_IMAGE_MODES)}"
            ))

        # 检查 visual_prompt 长度（过短或过长都可能有问题）
        if visual_prompt:
            if len(visual_prompt) < 20:
                issues.append(CheckIssue(
                    page_number=page_num,
                    severity="warning",
                    category="content",
                    message=f"图片 {img_idx + 1} 的 visual_prompt 过短（{len(visual_prompt)} 字符）",
                    suggestion="prompt 可能不够详细，建议补充更多描述"
                ))
            elif len(visual_prompt) > 2000:
                issues.append(CheckIssue(
                    page_number=page_num,
                    severity="warning",
                    category="redundancy",
                    message=f"图片 {img_idx + 1} 的 visual_prompt 过长（{len(visual_prompt)} 字符）",
                    suggestion="prompt 可能过于冗余，建议精简"
                ))

    return issues


def _deep_check_page(
    page: Dict[str, Any],
    llm_client,
    content_plan: Optional[Dict[str, Any]],
    style_config: Optional[Dict[str, Any]]
) -> Tuple[List[CheckIssue], Dict[int, str]]:
    """
    深度检查单个页面（调用 LLM 进行审阅和改进）

    返回：
    - issues: 问题列表
    - improved_prompts: {img_idx: improved_prompt}
    """
    issues = []
    improved_prompts = {}
    page_num = page.get('page_number', 0)
    images = page.get('images', [])

    for img_idx, img in enumerate(images):
        visual_prompt = (img.get('final_visual_prompt') or img.get('visual_prompt', '')).strip()
        if not visual_prompt:
            continue

        # 调用 LLM 审阅
        try:
            improved_prompt = _review_single_prompt(
                visual_prompt=visual_prompt,
                page=page,
                img=img,
                llm_client=llm_client,
                content_plan=content_plan,
                style_config=style_config
            )

            # 如果改进后的 prompt 与原 prompt 差异较大，记录为 info
            if improved_prompt != visual_prompt:
                diff_ratio = _calculate_diff_ratio(visual_prompt, improved_prompt)
                if diff_ratio > 0.3:  # 差异超过 30%
                    issues.append(CheckIssue(
                        page_number=page_num,
                        severity="info",
                        category="content",
                        message=f"图片 {img_idx + 1} 的 prompt 已优化（差异 {diff_ratio:.0%}）",
                        suggestion="建议使用优化后的 prompt"
                    ))
                    improved_prompts[img_idx] = improved_prompt

        except Exception as e:
            issues.append(CheckIssue(
                page_number=page_num,
                severity="warning",
                category="technical",
                message=f"图片 {img_idx + 1} 的深度审查失败：{str(e)}",
                suggestion="使用原 prompt"
            ))

    return issues, improved_prompts


def _review_single_prompt(
    visual_prompt: str,
    page: Dict[str, Any],
    img: Dict[str, Any],
    llm_client,
    content_plan: Optional[Dict[str, Any]],
    style_config: Optional[Dict[str, Any]]
) -> str:
    """
    使用 LLM 审阅单个 visual prompt

    这是从 ReviewerAgent 迁移过来的核心逻辑
    """
    page_num = page.get('page_number', 0)
    page_title = page.get('title', '')

    # 构建审阅 prompt
    review_prompt = _build_review_prompt(
        visual_prompt=visual_prompt,
        page_title=page_title,
        img_role=img.get('role', ''),
        img_mode=img.get('mode', ''),
        style_config=style_config or {}
    )

    # 调用 LLM
    response = llm_client.chat.completions.create(
        model=DEFAULT_LLM_MODEL,
        messages=[
            {"role": "system", "content": _get_review_system_prompt()},
            {"role": "user", "content": review_prompt}
        ],
        temperature=0.3
    )

    result = response.choices[0].message.content.strip()

    # 清理输出
    result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL | re.IGNORECASE).strip()
    result = re.sub(r'^```.*?\n', '', result)
    result = re.sub(r'```$', '', result).strip()

    return result


def _get_review_system_prompt() -> str:
    """获取审阅系统 prompt（从 ReviewerAgent 迁移）"""
    required_sections = format_prompt_sections()
    return f"""你是一位资深视觉设计师兼 PPT 艺术总监。你的任务是对执行 prompt 进行严格审阅和轻量优化。

## 审阅重点

### 1. 结构完整
确保 prompt 保留以下关键结构：
{required_sections}

### 2. 文字正确
确保：
- TEXT TO RENDER 中的文字与批准内容完全一致
- 不删减、不改写、不翻译、不补写
- 中文主文字强调正常、清晰、稳定渲染

### 3. 视觉忠实
确保：
- VISUAL SCENE 忠于当前页 visual description
- 当前页语义优先于 seed/reference
- seed 只控制视觉语法，不控制具体内容

### 4. 一致性
确保：
- 风格、配色、字体系统与整套 deck 一致
- 主文字字体系统稳定，不逐页漂移

### 5. 可执行性
确保：
- 指令无冲突
- 负向约束聚焦高价值故障
- 不因过度啰嗦而稀释重点

### 6. 精简优化
如果 prompt 已经足够好，可以原样返回。
如果需要修改，只做必要的小幅优化，优先删除重复、冲突和低价值废话。

## 输出格式

直接输出改进后的完整 prompt，不要解释，不要评论，不要 JSON，不要 markdown。"""


def _build_review_prompt(
    visual_prompt: str,
    page_title: str,
    img_role: str,
    img_mode: str,
    style_config: Dict[str, Any]
) -> str:
    """构建审阅 prompt"""
    palette = style_config.get('palette', [])
    fonts = style_config.get('fonts', [])

    prompt = f"""## 当前页信息
页面标题: {page_title}
图片作用: {img_role}
图片模式: {img_mode}

## 当前执行 prompt（需要审阅）
{visual_prompt}

## 风格配置
调色板: {', '.join(palette) if palette else '(未定义)'}
字体: {', '.join(fonts) if fonts else '(未定义)'}

## 审阅任务
请审阅上述执行 prompt，重点检查：
- 结构是否完整
- 文字是否准确
- 中文主文字规则是否清晰
- style / seed / reference 的边界是否清楚
- 是否有冗余、冲突、废话

如果需要优化，请输出改进后的完整 prompt。
如果已经足够好，可以直接原样返回。

直接输出改进后的完整 prompt："""

    return prompt


def _calculate_diff_ratio(text1: str, text2: str) -> float:
    """
    计算两个文本的差异比例（简单实现）

    返回 0.0-1.0 之间的值，1.0 表示完全不同
    """
    if not text1 or not text2:
        return 1.0

    # 简单的字符级差异计算
    len1, len2 = len(text1), len(text2)
    max_len = max(len1, len2)
    if max_len == 0:
        return 0.0

    # 计算长度差异
    len_diff = abs(len1 - len2) / max_len

    # 计算内容差异（简单的字符集合差异）
    set1 = set(text1.split())
    set2 = set(text2.split())
    if not set1 and not set2:
        return 0.0
    if not set1 or not set2:
        return 1.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)
    content_diff = 1.0 - (intersection / union if union > 0 else 0.0)

    # 综合长度和内容差异
    return (len_diff + content_diff) / 2


def print_review_report(report: ReviewReport):
    """友好地打印审查报告"""
    print("\n" + "=" * 60)
    print("Visual Prompt 审查报告")
    print("=" * 60)

    # 统计信息
    stats = report.stats
    print(f"\n📊 统计信息:")
    print(f"  总页数: {stats['total_pages']}")
    print(f"  已检查: {stats['checked_pages']} 页")
    print(f"    - 轻量检查: {stats['light_checked']} 页")
    print(f"    - 深度检查: {stats['deep_checked']} 页")
    print(f"  问题统计:")
    print(f"    - 错误: {stats['errors']}")
    print(f"    - 警告: {stats['warnings']}")
    print(f"    - 提示: {stats['infos']}")

    # 问题列表
    if report.issues:
        print(f"\n🔍 发现的问题:")
        for issue in report.issues:
            severity_icon = {
                "error": "❌",
                "warning": "⚠️",
                "info": "ℹ️"
            }.get(issue.severity, "•")

            print(f"\n  {severity_icon} P{issue.page_number} [{issue.category}]")
            print(f"     {issue.message}")
            if issue.suggestion:
                print(f"     💡 {issue.suggestion}")
    else:
        print(f"\n✅ 未发现问题")

    # 改进建议
    if report.patches:
        print(f"\n📝 改进建议:")
        print(f"  共 {len(report.patches)} 个 prompt 有优化版本")
        print(f"  可以使用这些改进后的 prompt 替换原 prompt")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        visual_plan_file = sys.argv[1]
        # 这里需要 llm_client，实际使用时需要传入
        print(f"审查文件：{visual_plan_file}")
        print("注意：命令行测试需要提供 llm_client")
