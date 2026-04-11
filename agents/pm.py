"""
PM Agent - 产品经理 Agent

负责接住用户输入并路由到正确阶段，是系统的入口和协调者。
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from ..utils.brief_manager import BriefManager, Brief
from ..utils.image_assets import ImageAssetsManager, ImageAsset, ImageMode

logger = logging.getLogger(__name__)


class PMAgent:
    """PM Agent - 负责用户输入接收、意图理解和流程路由"""

    def __init__(self, client, project_dir: str = "output"):
        """
        初始化 PM Agent

        Args:
            client: OpenAI 兼容客户端
            project_dir: 项目输出目录
        """
        self.client = client
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)

        # 初始化管理器
        self.brief_manager = BriefManager(str(self.project_dir / "brief.md"))
        self.image_assets_manager = ImageAssetsManager(
            str(self.project_dir / "image_assets.json"),
            client=client
        )

    def intake(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        接收用户输入，进行初步处理

        Args:
            user_input: 用户输入，可能包含：
                - text: 文本内容
                - images: 图片路径列表
                - template_pptx: 毛坯 PPT 路径
                - urls: 网络图片 URL 列表

        Returns:
            处理结果，包含下一步建议
        """
        logger.info("📥 PM Agent 接收用户输入")

        result = {
            "status": "success",
            "next_gate": None,
            "message": "",
        }

        try:
            # 1. 提取图片资产
            if user_input.get("images") or user_input.get("urls") or user_input.get("template_pptx"):
                self._extract_images_from_input(user_input)

            # 2. 整理用户意图
            if user_input.get("text"):
                self._organize_user_intent(user_input["text"])

            # 3. 判断当前应进入哪个 Gate
            next_gate = self.determine_gate()
            result["next_gate"] = next_gate
            result["message"] = f"建议进入 {next_gate} 阶段"

            return result

        except Exception as e:
            logger.error(f"PM Agent 处理失败: {e}")
            result["status"] = "error"
            result["message"] = str(e)
            return result

    def determine_gate(self) -> str:
        """
        判断当前应进入哪个 Gate

        Returns:
            Gate 名称：Content / Visual / Execute
        """
        # 检查是否有 brief
        brief = self.brief_manager.load()
        if not brief:
            return "Content"

        # 检查是否有 content_plan
        content_plan_path = self.project_dir / "content_plan.md"
        if not content_plan_path.exists():
            return "Content"

        # 检查是否有 visual_plan
        visual_plan_path = self.project_dir / "visual_plan.md"
        if not visual_plan_path.exists():
            return "Visual"

        # 都有了，进入执行阶段
        return "Execute"

    def _extract_images_from_input(self, user_input: Dict[str, Any]) -> None:
        """
        从用户输入中抽取图片资产

        Args:
            user_input: 用户输入
        """
        logger.info("🖼️ 开始抽取图片资产")

        # 1. 从本地路径列表抽取图片
        if user_input.get("images"):
            self._extract_from_local_paths(user_input["images"])

        # 2. 从 URL 列表下载图片
        if user_input.get("urls"):
            self._extract_from_urls(user_input["urls"])

        # 3. 从毛坯 PPTX 中提取图片
        if user_input.get("template_pptx"):
            self._extract_from_pptx(user_input["template_pptx"])

        # 4. 保存图片资产
        self.image_assets_manager.save_to_json()
        logger.info(f"✅ 图片资产抽取完成，共 {len(self.image_assets_manager.assets)} 张图片")

    def _extract_from_local_paths(self, image_paths: List[str]) -> None:
        """
        从本地路径列表抽取图片

        Args:
            image_paths: 图片路径列表
        """
        for path in image_paths:
            path_obj = Path(path)
            if not path_obj.exists():
                logger.warning(f"图片不存在: {path}")
                continue

            # 检查是否已存在
            if self.image_assets_manager.get_asset_by_path(path):
                logger.info(f"图片已存在，跳过: {path}")
                continue

            # 创建图片资产
            asset = ImageAsset(path=path)
            self.image_assets_manager.add_asset(asset)

            # 执行轻量读图
            try:
                result = self.image_assets_manager.light_read_image(path)
                if result:
                    logger.info(f"✅ 轻量读图完成: {path} -> {result.get('image_type')}")
                else:
                    logger.warning(f"轻量读图失败: {path}")
            except Exception as e:
                logger.error(f"轻量读图异常: {path} ({e})")

    def _extract_from_urls(self, urls: List[str]) -> None:
        """
        从 URL 列表下载图片

        Args:
            urls: 图片 URL 列表
        """
        import requests
        from urllib.parse import urlparse
        import hashlib

        for url in urls:
            try:
                # 下载图片
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                # 生成文件名（使用 URL hash）
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                parsed = urlparse(url)
                ext = Path(parsed.path).suffix or ".jpg"
                filename = f"downloaded_{url_hash}{ext}"
                save_path = self.project_dir / "images" / filename

                # 确保目录存在
                save_path.parent.mkdir(parents=True, exist_ok=True)

                # 保存图片
                with open(save_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"✅ 下载图片: {url} -> {save_path}")

                # 创建图片资产
                asset = ImageAsset(path=str(save_path))
                self.image_assets_manager.add_asset(asset)

                # 执行轻量读图
                try:
                    result = self.image_assets_manager.light_read_image(str(save_path))
                    if result:
                        logger.info(f"✅ 轻量读图完成: {save_path} -> {result.get('image_type')}")
                except Exception as e:
                    logger.error(f"轻量读图异常: {save_path} ({e})")

            except Exception as e:
                logger.error(f"下载图片失败: {url} ({e})")

    def _extract_from_pptx(self, pptx_path: str) -> None:
        """
        从毛坯 PPTX 中提取图片

        Args:
            pptx_path: PPTX 文件路径
        """
        try:
            from pptx import Presentation
        except ImportError:
            logger.error("需要安装 python-pptx: pip install python-pptx")
            return

        try:
            prs = Presentation(pptx_path)
            image_count = 0

            for slide_idx, slide in enumerate(prs.slides):
                for shape in slide.shapes:
                    # 检查是否是图片
                    if hasattr(shape, "image"):
                        image = shape.image
                        image_bytes = image.blob

                        # 生成文件名
                        ext = image.ext
                        filename = f"pptx_slide{slide_idx + 1}_img{image_count + 1}.{ext}"
                        save_path = self.project_dir / "images" / filename

                        # 确保目录存在
                        save_path.parent.mkdir(parents=True, exist_ok=True)

                        # 保存图片
                        with open(save_path, 'wb') as f:
                            f.write(image_bytes)

                        logger.info(f"✅ 提取图片: 第 {slide_idx + 1} 页 -> {save_path}")

                        # 创建图片资产
                        asset = ImageAsset(path=str(save_path))
                        self.image_assets_manager.add_asset(asset)

                        # 执行轻量读图
                        try:
                            result = self.image_assets_manager.light_read_image(str(save_path))
                            if result:
                                logger.info(f"✅ 轻量读图完成: {save_path} -> {result.get('image_type')}")
                        except Exception as e:
                            logger.error(f"轻量读图异常: {save_path} ({e})")

                        image_count += 1

            logger.info(f"✅ 从 PPTX 提取了 {image_count} 张图片")

        except Exception as e:
            logger.error(f"从 PPTX 提取图片失败: {pptx_path} ({e})")

    def _organize_user_intent(self, text: str) -> None:
        """
        将用户原始输入整理为结构化的任务约束

        Args:
            text: 用户文本输入
        """
        logger.info("📝 开始整理用户意图")

        # 构建 prompt
        prompt = f"""你是一个专业的产品经理，需要将用户的原始输入整理为结构化的任务约束。

用户输入：
{text}

请分析用户输入，提取以下信息（以 JSON 格式返回）：

1. input_type: 输入类型，从以下选项中选择一个
   - "topic": 只给了一个主题或标题
   - "article": 提供了完整的文章或长文本
   - "outline": 提供了大纲或结构化内容
   - "template_ppt": 基于已有的毛坯 PPT 进行修改
   - "add_images": 为已有内容补充图片
   - "modify_slide": 修改单个或少数几页

2. goal: 任务目标（一句话概括用户想做什么）

3. audience: 目标受众（如果用户提到了，否则为 null）

4. tone: 语气/风格（如果用户提到了，否则为 null）
   例如：专业、轻松、学术、商务等

5. constraints: 关键限制（列表，提取用户明确提到的约束）
   例如：页数限制、时间限制、必须包含的内容等

6. image_anchors: 图片位置意图（列表，提取用户提到的图片需求）
   每个元素包含：
   - anchor: 语义锚点（图片应该出现在哪个内容段落）
   - description: 图片描述或要求

返回格式：
{{
  "input_type": "...",
  "goal": "...",
  "audience": "..." or null,
  "tone": "..." or null,
  "constraints": [...],
  "image_anchors": [
    {{"anchor": "...", "description": "..."}},
    ...
  ]
}}

只返回 JSON，不要有其他内容。"""

        try:
            # 调用 LLM
            response = self.client.chat.completions.create(
                model="gemini-2.0-flash-exp",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            result_text = response.choices[0].message.content.strip()

            # 提取 JSON（去除可能的 markdown 包裹）
            import json
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()

            result = json.loads(result_text)

            logger.info(f"✅ 意图分析完成: {result['input_type']}")

            # 更新或创建 Brief
            brief = self.brief_manager.load()
            if not brief:
                # 创建新 Brief
                brief = Brief(
                    goal=result["goal"],
                    audience=result.get("audience"),
                    style_preference=result.get("tone"),
                    constraints=result.get("constraints", []),
                    image_requirements=result.get("image_anchors", []),
                )
                self.brief_manager.save(brief)
                logger.info("✅ 创建新 Brief")
            else:
                # 更新现有 Brief
                update_fields = {}
                if result.get("goal"):
                    update_fields["goal"] = result["goal"]
                if result.get("audience"):
                    update_fields["audience"] = result["audience"]
                if result.get("tone"):
                    update_fields["style_preference"] = result["tone"]
                if result.get("constraints"):
                    # 合并约束（去重）
                    existing = set(brief.constraints)
                    new_constraints = [c for c in result["constraints"] if c not in existing]
                    update_fields["constraints"] = brief.constraints + new_constraints
                if result.get("image_anchors"):
                    # 合并图片需求（去重）
                    existing_anchors = {req.get("anchor") for req in brief.image_requirements}
                    new_reqs = [req for req in result["image_anchors"] if req.get("anchor") not in existing_anchors]
                    update_fields["image_requirements"] = brief.image_requirements + new_reqs

                if update_fields:
                    self.brief_manager.update(**update_fields)
                    logger.info(f"✅ 更新 Brief: {list(update_fields.keys())}")

        except Exception as e:
            logger.error(f"整理用户意图失败: {e}")
            # 失败时创建一个最小化的 Brief
            brief = self.brief_manager.load()
            if not brief:
                brief = Brief(goal=text[:200])  # 使用前 200 字符作为 goal
                self.brief_manager.save(brief)
                logger.warning("⚠️ 使用简化 Brief")

    def final_intent_review(self) -> Dict[str, Any]:
        """
        执行前的最终意图审查

        检查项：
        1. 资源完整性（调用 resource_check）
        2. Prompt 质量（调用 prompt_guard）
        3. Brief 与 visual_plan 的一致性

        Returns:
            审查报告，包含：
            - passed: 是否通过审查
            - resource_check: 资源检查报告
            - prompt_review: Prompt 审查报告
            - consistency_check: 一致性检查结果
            - summary: 汇总信息
        """
        from ..utils.resource_check import check_resources, print_report as print_resource_report
        from ..utils.prompt_guard import review_visual_plan, print_review_report
        import json

        logger.info("🔍 开始最终意图审查")

        report = {
            "passed": False,
            "resource_check": None,
            "prompt_review": None,
            "consistency_check": None,
            "summary": {
                "total_issues": 0,
                "blocking_issues": 0,
                "warnings": 0,
            }
        }

        # 1. 资源完整性检查
        logger.info("📋 检查资源完整性...")
        try:
            resource_report = check_resources(
                output_dir=str(self.project_dir),
                check_images=True,
                check_placeholders=True,
                check_fields=True,
                check_consistency=True
            )
            report["resource_check"] = resource_report.to_dict()

            # 统计问题
            report["summary"]["total_issues"] += len(resource_report.issues)
            report["summary"]["blocking_issues"] += resource_report.summary.get("error", 0)
            report["summary"]["warnings"] += resource_report.summary.get("warning", 0)

            if not resource_report.passed:
                logger.warning(f"⚠️ 资源检查未通过：{resource_report.summary.get('error', 0)} 个错误")
                print_resource_report(resource_report)
            else:
                logger.info("✅ 资源检查通过")

        except Exception as e:
            logger.error(f"资源检查失败: {e}")
            report["resource_check"] = {"error": str(e)}
            report["summary"]["blocking_issues"] += 1

        # 2. Prompt 质量审查
        visual_plan_json = self.project_dir / "visual_plan.json"
        if visual_plan_json.exists():
            logger.info("📝 审查 Visual Prompt 质量...")
            try:
                prompt_review_report = review_visual_plan(
                    visual_plan_json_path=str(visual_plan_json),
                    llm_client=self.client,
                    strategy="auto",  # 自动策略：轻检查 + 种子页深查 + 异常页必查
                    seed_pages=[1],  # 第一页作为种子页
                    content_plan_json_path=str(self.project_dir / "content_plan.json"),
                    style_config=None
                )
                report["prompt_review"] = prompt_review_report.to_dict()

                # 统计问题
                report["summary"]["total_issues"] += len(prompt_review_report.issues)
                report["summary"]["blocking_issues"] += prompt_review_report.stats.get("errors", 0)
                report["summary"]["warnings"] += prompt_review_report.stats.get("warnings", 0)

                if prompt_review_report.stats.get("errors", 0) > 0:
                    logger.warning(f"⚠️ Prompt 审查发现 {prompt_review_report.stats['errors']} 个错误")
                    print_review_report(prompt_review_report)
                else:
                    logger.info("✅ Prompt 审查通过")

            except Exception as e:
                logger.error(f"Prompt 审查失败: {e}")
                report["prompt_review"] = {"error": str(e)}
                report["summary"]["warnings"] += 1
        else:
            logger.warning("⚠️ visual_plan.json 不存在，跳过 Prompt 审查")
            report["prompt_review"] = {"skipped": "visual_plan.json not found"}

        # 3. Brief 与 visual_plan 的一致性检查
        logger.info("🔗 检查 Brief 与 Visual Plan 的一致性...")
        try:
            consistency_issues = self._check_brief_visual_consistency()
            report["consistency_check"] = consistency_issues

            if consistency_issues:
                report["summary"]["total_issues"] += len(consistency_issues)
                report["summary"]["warnings"] += len(consistency_issues)
                logger.warning(f"⚠️ 发现 {len(consistency_issues)} 个一致性问题")
                for issue in consistency_issues:
                    logger.warning(f"  - {issue}")
            else:
                logger.info("✅ 一致性检查通过")

        except Exception as e:
            logger.error(f"一致性检查失败: {e}")
            report["consistency_check"] = {"error": str(e)}
            report["summary"]["warnings"] += 1

        # 4. 判断是否通过
        report["passed"] = report["summary"]["blocking_issues"] == 0

        # 5. 打印汇总
        logger.info("\n" + "=" * 60)
        logger.info("最终意图审查报告")
        logger.info("=" * 60)
        if report["passed"]:
            logger.info("✅ 审查通过，可以执行")
        else:
            logger.error(f"❌ 审查未通过，发现 {report['summary']['blocking_issues']} 个阻塞问题")

        logger.info(f"\n问题统计:")
        logger.info(f"  总问题数: {report['summary']['total_issues']}")
        logger.info(f"  阻塞问题: {report['summary']['blocking_issues']}")
        logger.info(f"  警告: {report['summary']['warnings']}")
        logger.info("=" * 60 + "\n")

        return report

    def _check_brief_visual_consistency(self) -> List[str]:
        """
        检查 Brief 与 visual_plan 的一致性

        Returns:
            一致性问题列表
        """
        import json

        issues = []

        # 加载 Brief
        brief = self.brief_manager.load()
        if not brief:
            issues.append("Brief 文件不存在")
            return issues

        # 加载 visual_plan.json
        visual_plan_json = self.project_dir / "visual_plan.json"
        if not visual_plan_json.exists():
            issues.append("visual_plan.json 文件不存在")
            return issues

        try:
            with open(visual_plan_json, 'r', encoding='utf-8') as f:
                visual_plan = json.load(f)
        except Exception as e:
            issues.append(f"无法读取 visual_plan.json: {e}")
            return issues

        # 检查图片需求是否被满足
        if brief.image_requirements:
            brief_anchors = {req.get("anchor") for req in brief.image_requirements if req.get("anchor")}
            visual_anchors = set()

            for page in visual_plan.get("pages", []):
                for img in page.get("images", []):
                    anchor = img.get("semantic_anchor")
                    if anchor:
                        visual_anchors.add(anchor)

            # 检查是否有未满足的图片需求
            missing_anchors = brief_anchors - visual_anchors
            if missing_anchors:
                issues.append(f"Brief 中的图片需求未在 visual_plan 中体现: {', '.join(missing_anchors)}")

        # 检查风格偏好是否一致
        if brief.style_preference:
            # 这里可以进一步检查 visual_plan 中的 prompt 是否符合风格偏好
            # 简化实现：只检查是否有风格配置
            style_mentioned = False
            for page in visual_plan.get("pages", []):
                for img in page.get("images", []):
                    prompt = img.get("visual_prompt", "")
                    if brief.style_preference.lower() in prompt.lower():
                        style_mentioned = True
                        break
                if style_mentioned:
                    break

            if not style_mentioned:
                issues.append(f"Brief 中的风格偏好「{brief.style_preference}」未在 visual_plan 的 prompt 中体现")

        return issues

    def analyze_modification(self, modification_request: str, target_pages: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        分析用户的修改请求，判断应该回退到哪个 Gate

        Args:
            modification_request: 用户的修改请求文本
            target_pages: 目标页面编号列表（如果用户指定了具体页面）

        Returns:
            分析结果，包含：
            - modification_type: 修改类型（content/visual/structure/image_assignment）
            - rollback_to_gate: 应回退到的 Gate（Content/Visual/Execute）
            - can_modify_single_page: 是否可以只修改单页
            - affected_pages: 受影响的页面编号列表
            - reason: 判断理由
            - suggestions: 操作建议
        """
        import json

        logger.info("🔍 分析修改请求")

        result = {
            "modification_type": None,
            "rollback_to_gate": None,
            "can_modify_single_page": False,
            "affected_pages": target_pages or [],
            "reason": "",
            "suggestions": []
        }

        # 构建分析 prompt
        prompt = f"""你是一个专业的产品经理，需要分析用户的修改请求，判断应该回退到哪个处理阶段。

系统有三个处理阶段（Gate）：
1. Content Gate: 内容规划阶段，生成 content_plan（页面结构、标题、文本内容）
2. Visual Gate: 视觉规划阶段，生成 visual_plan（图片选择、位置、视觉 prompt）
3. Execute Gate: 执行阶段，生成最终的 PPT 文件

用户修改请求：
{modification_request}

{"用户指定的目标页面: " + str(target_pages) if target_pages else "用户未指定具体页面"}

请分析这个修改请求，返回 JSON 格式的分析结果：

{{
  "modification_type": "修改类型，从以下选项中选择一个：content（内容修改）/ visual（视觉修改）/ structure（结构修改）/ image_assignment（图片归属修改）",
  "rollback_to_gate": "应回退到的 Gate，从以下选项中选择一个：Content / Visual / Execute",
  "can_modify_single_page": true/false,
  "reason": "判断理由（一句话说明为什么要回退到这个 Gate）",
  "suggestions": ["操作建议1", "操作建议2"]
}}

判断规则：
1. 修改类型判断：
   - content: 修改文字内容、标题、页面数量、页面顺序
   - visual: 修改图片选择、图片位置、视觉风格、prompt
   - structure: 修改整体结构、增删页面、重新组织内容
   - image_assignment: 修改图片与页面的对应关系、图片语义锚点

2. Gate 回退判断：
   - 回退到 Content: 如果修改涉及内容结构、页面数量、文字内容
   - 回退到 Visual: 如果修改只涉及图片选择、位置、视觉效果
   - 回退到 Execute: 如果修改只涉及 PPT 生成参数、格式调整

3. 单页修改判断：
   - 可以单页修改: 修改只影响特定页面的视觉效果或文字内容，不影响其他页面
   - 不能单页修改: 修改涉及整体结构、页面顺序、或影响多个页面的一致性

只返回 JSON，不要有其他内容。"""

        try:
            # 调用 LLM 分析
            response = self.client.chat.completions.create(
                model="gemini-2.0-flash-exp",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            result_text = response.choices[0].message.content.strip()

            # 提取 JSON
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()

            analysis = json.loads(result_text)

            # 更新结果
            result["modification_type"] = analysis.get("modification_type")
            result["rollback_to_gate"] = analysis.get("rollback_to_gate")
            result["can_modify_single_page"] = analysis.get("can_modify_single_page", False)
            result["reason"] = analysis.get("reason", "")
            result["suggestions"] = analysis.get("suggestions", [])

            # 如果用户指定了页面，且判断可以单页修改，则只影响指定页面
            if target_pages and result["can_modify_single_page"]:
                result["affected_pages"] = target_pages
            else:
                # 否则影响所有页面
                result["affected_pages"] = self._get_all_page_numbers()

            logger.info(f"✅ 修改分析完成: {result['modification_type']} -> {result['rollback_to_gate']}")
            logger.info(f"   理由: {result['reason']}")
            logger.info(f"   单页修改: {result['can_modify_single_page']}")
            logger.info(f"   受影响页面: {result['affected_pages']}")

            return result

        except Exception as e:
            logger.error(f"修改分析失败: {e}")
            # 返回保守的默认值
            result["modification_type"] = "unknown"
            result["rollback_to_gate"] = "Content"
            result["can_modify_single_page"] = False
            result["reason"] = f"分析失败，保守起见回退到 Content Gate: {e}"
            result["suggestions"] = ["建议手动检查修改范围"]
            result["affected_pages"] = self._get_all_page_numbers()
            return result

    def _get_all_page_numbers(self) -> List[int]:
        """
        获取所有页面编号

        Returns:
            页面编号列表
        """
        import json

        # 尝试从 content_plan.json 获取
        content_plan_json = self.project_dir / "content_plan.json"
        if content_plan_json.exists():
            try:
                with open(content_plan_json, 'r', encoding='utf-8') as f:
                    content_plan = json.load(f)
                    slides = content_plan.get("slides", [])
                    return [slide.get("slide_number", i + 1) for i, slide in enumerate(slides)]
            except Exception:
                pass

        # 尝试从 visual_plan.json 获取
        visual_plan_json = self.project_dir / "visual_plan.json"
        if visual_plan_json.exists():
            try:
                with open(visual_plan_json, 'r', encoding='utf-8') as f:
                    visual_plan = json.load(f)
                    pages = visual_plan.get("pages", [])
                    return [page.get("page_number", i + 1) for i, page in enumerate(pages)]
            except Exception:
                pass

        # 默认返回空列表
        return []
