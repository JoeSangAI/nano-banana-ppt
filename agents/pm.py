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
