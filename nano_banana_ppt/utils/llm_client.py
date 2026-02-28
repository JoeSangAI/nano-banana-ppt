"""
LLM 调用工具：支持 429 配额耗尽时自动切换备用模型

会话策略：本任务内若某模型返回 429，后续调用直接跳过该模型；
新任务（plan/execute 开始时）会重置，重新从主模型尝试。
"""
import logging
from typing import List, Optional, Set

logger = logging.getLogger(__name__)

# 主模型 → 备用模型链（当主模型 429 时依次尝试）
MODEL_FALLBACK_CHAIN: List[str] = [
    "gemini-3.1-pro-preview",    # 主模型
    "gemini-3-pro-preview",      # 备用 1：3.0 Pro
    "gemini-3-flash-preview",    # 备用 2：3.0 Flash
]

# 本任务内已确认 429 的模型，后续调用直接跳过
_session_exhausted_models: Set[str] = set()


def reset_session():
    """新任务开始时调用，重置 429 记忆，下个任务重新从主模型尝试"""
    global _session_exhausted_models
    if _session_exhausted_models:
        logger.info(f"🔄 新任务开始，重置模型选择（上一任务耗尽的模型: {_session_exhausted_models}）")
    _session_exhausted_models.clear()


def _is_quota_exceeded(e: Exception) -> bool:
    """判断是否为 429 配额耗尽（可重试并切换模型）"""
    err_str = str(e).lower()
    if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
        return True
    if hasattr(e, "status_code") and e.status_code == 429:
        return True
    if hasattr(e, "response") and hasattr(e.response, "status_code") and e.response.status_code == 429:
        return True
    return False


def chat_completion_with_fallback(
    client,
    model: Optional[str] = None,
    model_fallback: Optional[List[str]] = None,
    **kwargs,
):
    """
    调用 chat.completions.create，遇 429 时自动切换备用模型。

    Args:
        client: OpenAI 兼容客户端
        model: 首选模型，默认用链中第一个
        model_fallback: 自定义备用模型列表，默认用 MODEL_FALLBACK_CHAIN
        **kwargs: 传给 client.chat.completions.create 的参数 (messages, temperature 等)

    Returns:
        response 对象（与原生 create 一致）

    Raises:
        最后一次尝试的异常（若全部失败）
    """
    models = model_fallback or MODEL_FALLBACK_CHAIN
    if model:
        models = [model] + [m for m in models if m != model]
    else:
        model = models[0]

    # 本任务内已 429 的模型直接跳过
    models = [m for m in models if m not in _session_exhausted_models]
    if not models:
        raise RuntimeError("所有备用模型均已在本次任务中因 429 被跳过，请新开任务重试")

    last_error = None
    for i, m in enumerate(models):
        try:
            resp = client.chat.completions.create(model=m, **kwargs)
            if i > 0 or m != (model_fallback or MODEL_FALLBACK_CHAIN)[0]:
                logger.info(f"✅ 使用模型 {m} 完成调用")
            return resp
        except Exception as e:
            last_error = e
            if _is_quota_exceeded(e):
                _session_exhausted_models.add(m)
                if i < len(models) - 1:
                    logger.warning(f"⚠️ 模型 {m} 配额已耗尽 (429)，本任务后续调用将跳过该模型，尝试: {models[i + 1]}")
                else:
                    raise
            else:
                raise

    if last_error:
        raise last_error
