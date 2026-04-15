"""
统一的模型 / Provider 配置。

- 所有 LLM / VLM 请求默认走 MiniMax OpenAI 兼容接口
- 所有图片生成 / 放大请求默认走 DeerAPI
"""

import os
from typing import Optional


DEFAULT_LLM_MODEL = "MiniMax-M2.7"
DEFAULT_LLM_API_BASE = "https://api.minimaxi.com/v1"

DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_IMAGE_API_BASE = "https://api.deerapi.com/v1"


def get_llm_api_key(explicit: Optional[str] = None) -> Optional[str]:
    return explicit or os.getenv("OPENAI_API_KEY")


def get_llm_api_base(explicit: Optional[str] = None) -> str:
    return explicit or os.getenv("OPENAI_API_BASE") or DEFAULT_LLM_API_BASE


def get_image_api_key(explicit: Optional[str] = None, fallback: Optional[str] = None) -> Optional[str]:
    return explicit or os.getenv("IMAGE_GEN_API_KEY") or fallback


def get_image_api_base(explicit: Optional[str] = None) -> str:
    return explicit or os.getenv("IMAGE_GEN_API_BASE") or DEFAULT_IMAGE_API_BASE
