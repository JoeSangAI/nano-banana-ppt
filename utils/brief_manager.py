"""
Brief 文件管理模块

Brief 是任务意图的唯一真相源，以 Markdown 格式存储，使用 YAML frontmatter。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
import yaml
import re


@dataclass
class Brief:
    """Brief 数据类"""

    goal: str  # 任务目标
    audience: Optional[str] = None  # 目标受众
    style_preference: Optional[str] = None  # 风格偏好
    constraints: List[str] = field(default_factory=list)  # 约束条件
    image_requirements: List[Dict[str, str]] = field(default_factory=list)  # 图片需求

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "goal": self.goal,
            "audience": self.audience,
            "style_preference": self.style_preference,
            "constraints": self.constraints,
            "image_requirements": self.image_requirements,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Brief":
        """从字典创建实例"""
        return cls(
            goal=data.get("goal", ""),
            audience=data.get("audience"),
            style_preference=data.get("style_preference"),
            constraints=data.get("constraints", []),
            image_requirements=data.get("image_requirements", []),
        )


class BriefManager:
    """Brief 文件管理器"""

    def __init__(self, brief_file: Optional[str] = None):
        """
        初始化 Brief 管理器

        Args:
            brief_file: Brief 文件路径，默认为 output/brief.md
        """
        self.brief_file = brief_file or "output/brief.md"
        self.brief: Optional[Brief] = None

    def load(self) -> Optional[Brief]:
        """
        从文件加载 Brief

        Returns:
            Brief 对象，如果文件不存在返回 None
        """
        if not Path(self.brief_file).exists():
            return None

        try:
            with open(self.brief_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析 YAML frontmatter
            match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
            if not match:
                raise ValueError("Brief 文件格式错误：缺少 YAML frontmatter")

            frontmatter = yaml.safe_load(match.group(1))
            body = match.group(2).strip()

            # 创建 Brief 对象
            self.brief = Brief.from_dict(frontmatter)

            return self.brief

        except Exception as e:
            import logging
            logging.error(f"加载 Brief 失败: {self.brief_file} ({e})")
            raise

    def save(self, brief: Brief) -> None:
        """
        保存 Brief 到文件

        Args:
            brief: Brief 对象
        """
        try:
            # 确保输出目录存在
            output_dir = Path(self.brief_file).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # 构建 YAML frontmatter
            frontmatter = yaml.dump(
                brief.to_dict(),
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False
            )

            # 构建 Markdown 内容
            content = f"---\n{frontmatter}---\n\n# Brief\n\n## 任务目标\n\n{brief.goal}\n"

            if brief.audience:
                content += f"\n## 目标受众\n\n{brief.audience}\n"

            if brief.style_preference:
                content += f"\n## 风格偏好\n\n{brief.style_preference}\n"

            if brief.constraints:
                content += "\n## 约束条件\n\n"
                for constraint in brief.constraints:
                    content += f"- {constraint}\n"

            if brief.image_requirements:
                content += "\n## 图片需求\n\n"
                for req in brief.image_requirements:
                    content += f"- **{req.get('anchor', '')}**: {req.get('description', '')}\n"

            # 写入文件
            with open(self.brief_file, 'w', encoding='utf-8') as f:
                f.write(content)

            self.brief = brief

        except Exception as e:
            import logging
            logging.error(f"保存 Brief 失败: {self.brief_file} ({e})")
            raise

    def update(self, **kwargs) -> None:
        """
        更新 Brief 的部分字段

        Args:
            **kwargs: 要更新的字段
        """
        if not self.brief:
            raise ValueError("Brief 未加载，请先调用 load() 或 save()")

        for key, value in kwargs.items():
            if hasattr(self.brief, key):
                setattr(self.brief, key, value)

        self.save(self.brief)
