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
        从用户输入中抽取图片资产（占位实现）

        Args:
            user_input: 用户输入
        """
        # TODO: US-006 将实现完整的图片抽取逻辑
        logger.info("🖼️ 抽取图片资产（占位实现）")
        pass

    def _organize_user_intent(self, text: str) -> None:
        """
        将用户原始输入整理为结构化的任务约束（占位实现）

        Args:
            text: 用户文本输入
        """
        # TODO: US-007 将实现完整的意图整理逻辑
        logger.info("📝 整理用户意图（占位实现）")
        pass
