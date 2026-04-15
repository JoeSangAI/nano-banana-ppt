"""
资源完整性检查工具

在执行前检查所有资源是否完整，包括：
- 图片路径是否存在
- 待补图是否已处理
- 必填字段是否完整
- brief/content_plan/visual_plan 是否一致
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class CheckIssue:
    """检查问题"""
    severity: str  # "error" | "warning" | "info"
    category: str  # "missing_file" | "placeholder" | "missing_field" | "inconsistency"
    message: str
    location: str  # 问题位置（文件名、页码等）


@dataclass
class ResourceCheckReport:
    """资源检查报告"""
    passed: bool
    issues: List[CheckIssue]
    summary: Dict[str, int]  # 按 severity 统计问题数量

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": [
                {
                    "severity": issue.severity,
                    "category": issue.category,
                    "message": issue.message,
                    "location": issue.location
                }
                for issue in self.issues
            ],
            "summary": self.summary
        }


def check_resources(
    output_dir: str,
    check_images: bool = True,
    check_placeholders: bool = True,
    check_fields: bool = True,
    check_consistency: bool = True
) -> ResourceCheckReport:
    """
    检查资源完整性

    Args:
        output_dir: 输出目录路径
        check_images: 是否检查图片路径
        check_placeholders: 是否检查待补图
        check_fields: 是否检查必填字段
        check_consistency: 是否检查一致性

    Returns:
        ResourceCheckReport: 检查报告
    """
    issues: List[CheckIssue] = []
    output_path = Path(output_dir)

    # 检查必要文件是否存在
    brief_path = output_path / "brief.md"
    content_plan_md = output_path / "content_plan.md"
    content_plan_json = output_path / "content_plan.json"
    visual_plan_md = output_path / "visual_plan.md"
    visual_plan_json = output_path / "visual_plan.json"
    image_assets_json = output_path / "image_assets.json"

    if not brief_path.exists():
        issues.append(CheckIssue(
            severity="error",
            category="missing_file",
            message="brief.md 文件不存在",
            location=str(brief_path)
        ))

    if not content_plan_md.exists():
        issues.append(CheckIssue(
            severity="error",
            category="missing_file",
            message="content_plan.md 文件不存在",
            location=str(content_plan_md)
        ))

    if not content_plan_json.exists():
        issues.append(CheckIssue(
            severity="warning",
            category="missing_file",
            message="content_plan.json 文件不存在（需要编译）",
            location=str(content_plan_json)
        ))

    if not visual_plan_md.exists():
        issues.append(CheckIssue(
            severity="error",
            category="missing_file",
            message="visual_plan.md 文件不存在",
            location=str(visual_plan_md)
        ))

    if not visual_plan_json.exists():
        issues.append(CheckIssue(
            severity="warning",
            category="missing_file",
            message="visual_plan.json 文件不存在（需要编译）",
            location=str(visual_plan_json)
        ))

    if not image_assets_json.exists():
        issues.append(CheckIssue(
            severity="warning",
            category="missing_file",
            message="image_assets.json 文件不存在",
            location=str(image_assets_json)
        ))

    # 如果关键文件缺失，直接返回
    if any(issue.severity == "error" for issue in issues):
        return _build_report(issues)

    # 检查图片资产
    image_assets = {}
    if image_assets_json.exists():
        try:
            with open(image_assets_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                image_assets = {asset['path']: asset for asset in data.get('assets', [])}
        except Exception as e:
            issues.append(CheckIssue(
                severity="error",
                category="missing_file",
                message=f"无法读取 image_assets.json: {e}",
                location=str(image_assets_json)
            ))

    # 检查 visual_plan.json
    if visual_plan_json.exists() and check_images:
        try:
            with open(visual_plan_json, 'r', encoding='utf-8') as f:
                visual_plan = json.load(f)

            for page in visual_plan.get('pages', []):
                page_num = page.get('page_number', '?')
                page_title = page.get('title', '未命名')

                for img_idx, img in enumerate(page.get('images', [])):
                    img_path = img.get('path', '')

                    # 检查待补图
                    if check_placeholders and img_path == "PLACEHOLDER":
                        issues.append(CheckIssue(
                            severity="error",
                            category="placeholder",
                            message=f"页面 {page_num} 「{page_title}」存在待补图占位符",
                            location=f"page_{page_num}_image_{img_idx}"
                        ))
                        continue

                    # 检查图片路径是否存在
                    if check_images and img_path and img_path != "__GENERATED__":
                        # 尝试相对路径和绝对路径
                        img_full_path = Path(img_path)
                        if not img_full_path.is_absolute():
                            img_full_path = output_path / img_path

                        if not img_full_path.exists():
                            issues.append(CheckIssue(
                                severity="error",
                                category="missing_file",
                                message=f"页面 {page_num} 「{page_title}」的图片文件不存在: {img_path}",
                                location=f"page_{page_num}_image_{img_idx}"
                            ))

                    # 检查必填字段
                    if check_fields:
                        if not img.get('mode'):
                            issues.append(CheckIssue(
                                severity="error",
                                category="missing_field",
                                message=f"页面 {page_num} 「{page_title}」的图片缺少 mode 字段",
                                location=f"page_{page_num}_image_{img_idx}"
                            ))

                        if not img.get('final_visual_prompt') and not img.get('visual_prompt'):
                            issues.append(CheckIssue(
                                severity="warning",
                                category="missing_field",
                                message=f"页面 {page_num} 「{page_title}」的图片缺少 final_visual_prompt",
                                location=f"page_{page_num}_image_{img_idx}"
                            ))

        except Exception as e:
            issues.append(CheckIssue(
                severity="error",
                category="missing_file",
                message=f"无法读取 visual_plan.json: {e}",
                location=str(visual_plan_json)
            ))

    # 检查一致性
    if check_consistency and content_plan_json.exists() and visual_plan_json.exists():
        try:
            with open(content_plan_json, 'r', encoding='utf-8') as f:
                content_plan = json.load(f)

            with open(visual_plan_json, 'r', encoding='utf-8') as f:
                visual_plan = json.load(f)

            content_slides = content_plan.get('slides', [])
            visual_pages = visual_plan.get('pages', [])

            # 检查页数是否一致
            if len(content_slides) != len(visual_pages):
                issues.append(CheckIssue(
                    severity="warning",
                    category="inconsistency",
                    message=f"content_plan 有 {len(content_slides)} 页，visual_plan 有 {len(visual_pages)} 页，数量不一致",
                    location="content_plan.json vs visual_plan.json"
                ))

            # 检查标题是否一致
            for i, (content_slide, visual_page) in enumerate(zip(content_slides, visual_pages)):
                content_title = content_slide.get('title', '')
                visual_title = visual_page.get('title', '')
                if '·' in visual_title:
                    visual_title = visual_title.split('·', 1)[1].strip()

                if content_title != visual_title:
                    issues.append(CheckIssue(
                        severity="info",
                        category="inconsistency",
                        message=f"页面 {i+1} 标题不一致: content=「{content_title}」vs visual=「{visual_title}」",
                        location=f"page_{i+1}"
                    ))

        except Exception as e:
            issues.append(CheckIssue(
                severity="warning",
                category="inconsistency",
                message=f"无法检查一致性: {e}",
                location="content_plan.json vs visual_plan.json"
            ))

    return _build_report(issues)


def _build_report(issues: List[CheckIssue]) -> ResourceCheckReport:
    """构建检查报告"""
    summary = {
        "error": sum(1 for issue in issues if issue.severity == "error"),
        "warning": sum(1 for issue in issues if issue.severity == "warning"),
        "info": sum(1 for issue in issues if issue.severity == "info")
    }

    passed = summary["error"] == 0

    return ResourceCheckReport(
        passed=passed,
        issues=issues,
        summary=summary
    )


def print_report(report: ResourceCheckReport) -> None:
    """打印检查报告"""
    print("\n" + "="*60)
    print("资源完整性检查报告")
    print("="*60)

    if report.passed:
        print("✅ 检查通过")
    else:
        print("❌ 检查失败")

    print(f"\n问题统计:")
    print(f"  错误: {report.summary['error']}")
    print(f"  警告: {report.summary['warning']}")
    print(f"  信息: {report.summary['info']}")

    if report.issues:
        print("\n问题详情:")
        for issue in report.issues:
            icon = "❌" if issue.severity == "error" else "⚠️" if issue.severity == "warning" else "ℹ️"
            print(f"\n{icon} [{issue.severity.upper()}] {issue.category}")
            print(f"   {issue.message}")
            print(f"   位置: {issue.location}")

    print("\n" + "="*60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python resource_check.py <output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]
    report = check_resources(output_dir)
    print_report(report)

    sys.exit(0 if report.passed else 1)
