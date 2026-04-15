"""
图片资产管理模块

定义图片模式枚举和图片资产数据结构，用于管理 PPT 生成过程中的图片资源。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
import json

from .provider_config import DEFAULT_LLM_MODEL


class ImageMode(Enum):
    """图片处理模式枚举"""

    INTENT_FUSION = "intent_fusion"  # 意向融合：只取语义，不保留可识别性
    ELEMENT_PRESERVE = "element_preserve"  # 元素保留：保留主体，允许重组
    ORIGINAL_PRESENT = "original_present"  # 原图呈现：保留长宽比，轻微加工


@dataclass
class ImageAsset:
    """图片资产数据类"""

    path: str  # 图片路径
    mode: Optional[ImageMode] = None  # 图片处理模式
    semantic_anchor: Optional[str] = None  # 语义锚点（如"客户案例章节"）
    role: Optional[str] = None  # 图片角色（如"背景图"、"产品展示"）
    status: str = "pending"  # 状态：pending/processed/failed

    # 轻量读图结果
    image_type: Optional[str] = None  # 图片类型：截图/人物/产品/图表/场景
    description: Optional[str] = None  # 简短描述
    recommended_mode: Optional[ImageMode] = None  # 推荐的处理模式

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "path": self.path,
            "mode": self.mode.value if self.mode else None,
            "semantic_anchor": self.semantic_anchor,
            "role": self.role,
            "status": self.status,
            "image_type": self.image_type,
            "description": self.description,
            "recommended_mode": self.recommended_mode.value if self.recommended_mode else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageAsset":
        """从字典创建实例"""
        mode = ImageMode(data["mode"]) if data.get("mode") else None
        recommended_mode = ImageMode(data["recommended_mode"]) if data.get("recommended_mode") else None

        return cls(
            path=data["path"],
            mode=mode,
            semantic_anchor=data.get("semantic_anchor"),
            role=data.get("role"),
            status=data.get("status", "pending"),
            image_type=data.get("image_type"),
            description=data.get("description"),
            recommended_mode=recommended_mode,
        )


class ImageAssetsManager:
    """图片资产管理器"""

    def __init__(self, assets_file: Optional[str] = None, client=None):
        """
        初始化图片资产管理器

        Args:
            assets_file: 图片资产 JSON 文件路径，默认为 output/image_assets.json
            client: OpenAI 兼容客户端，用于调用 VLM
        """
        self.assets_file = assets_file or "output/image_assets.json"
        self.assets: List[ImageAsset] = []
        self.client = client

    def add_asset(self, asset: ImageAsset) -> None:
        """添加图片资产"""
        self.assets.append(asset)

    def get_asset_by_path(self, path: str) -> Optional[ImageAsset]:
        """根据路径获取图片资产"""
        for asset in self.assets:
            if asset.path == path:
                return asset
        return None

    def get_assets_by_anchor(self, anchor: str) -> List[ImageAsset]:
        """根据语义锚点获取图片资产"""
        return [asset for asset in self.assets if asset.semantic_anchor == anchor]

    def light_read_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        对图片进行轻量读图，判断图片类型和推荐模式

        Args:
            image_path: 图片路径

        Returns:
            包含 image_type, description, recommended_mode 的字典，失败返回 None
        """
        if not self.client:
            raise ValueError("需要提供 client 才能使用轻量读图功能")

        if not Path(image_path).exists():
            return None

        try:
            # 读取并编码图片
            from PIL import Image
            import base64
            from io import BytesIO

            with Image.open(image_path) as img:
                img = img.convert("RGB")
                # 缩放以降低 token 消耗
                img.thumbnail((512, 512))
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                img_b64 = base64.b64encode(buffered.getvalue()).decode()

            # 构建 prompt
            prompt = """分析这张图片，判断它的类型和最适合的处理模式。

请输出一个 JSON 对象，包含以下字段：
- "image_type": 图片类型，从以下选项中选择一个：["截图", "人物", "产品", "图表", "场景"]
- "description": 简短描述（1-2句话，描述图片的主要内容）
- "recommended_mode": 推荐的处理模式，从以下选项中选择一个：
  * "intent_fusion" - 意向融合：只取语义，不保留可识别性（适合氛围图、场景图）
  * "element_preserve" - 元素保留：保留主体，允许重组（适合人物、产品）
  * "original_present" - 原图呈现：保留长宽比，轻微加工（适合截图、图表、精确信息）

只输出 JSON，不要包含 markdown 代码块标记。"""

            # 调用 VLM
            response = self.client.chat.completions.create(
                model=DEFAULT_LLM_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                        ]
                    }
                ],
                temperature=0.1
            )

            content = response.choices[0].message.content.strip()

            # 提取 JSON
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                json_str = content[start:end+1]
                result = json.loads(json_str)

                # 更新对应的 ImageAsset
                asset = self.get_asset_by_path(image_path)
                if asset:
                    asset.image_type = result.get("image_type")
                    asset.description = result.get("description")
                    mode_str = result.get("recommended_mode")
                    if mode_str:
                        asset.recommended_mode = ImageMode(mode_str)

                return result
            else:
                return None

        except Exception as e:
            import logging
            logging.warning(f"轻量读图失败: {image_path} ({e})")
            return None

    def save_to_json(self) -> None:
        """
        将图片资产保存到 JSON 文件
        """
        try:
            # 确保输出目录存在
            output_dir = Path(self.assets_file).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # 转换为字典列表
            data = {
                "assets": [asset.to_dict() for asset in self.assets]
            }

            # 写入文件
            with open(self.assets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            import logging
            logging.error(f"保存图片资产失败: {self.assets_file} ({e})")
            raise

    def load_from_json(self) -> None:
        """
        从 JSON 文件加载图片资产
        支持增量更新：不覆盖已有的轻量读图结果
        """
        if not Path(self.assets_file).exists():
            return

        try:
            with open(self.assets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            loaded_assets = [ImageAsset.from_dict(item) for item in data.get("assets", [])]

            # 增量更新：合并已有资产和新加载的资产
            for loaded_asset in loaded_assets:
                existing_asset = self.get_asset_by_path(loaded_asset.path)
                if existing_asset:
                    # 如果已有资产，只更新空字段（不覆盖已有的轻量读图结果）
                    if not existing_asset.image_type and loaded_asset.image_type:
                        existing_asset.image_type = loaded_asset.image_type
                    if not existing_asset.description and loaded_asset.description:
                        existing_asset.description = loaded_asset.description
                    if not existing_asset.recommended_mode and loaded_asset.recommended_mode:
                        existing_asset.recommended_mode = loaded_asset.recommended_mode
                    if not existing_asset.mode and loaded_asset.mode:
                        existing_asset.mode = loaded_asset.mode
                    if not existing_asset.semantic_anchor and loaded_asset.semantic_anchor:
                        existing_asset.semantic_anchor = loaded_asset.semantic_anchor
                    if not existing_asset.role and loaded_asset.role:
                        existing_asset.role = loaded_asset.role
                else:
                    # 如果不存在，直接添加
                    self.assets.append(loaded_asset)

        except Exception as e:
            import logging
            logging.error(f"加载图片资产失败: {self.assets_file} ({e})")
            raise
