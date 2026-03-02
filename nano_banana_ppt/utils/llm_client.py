"""
LLM 调用工具：支持 429/503 时自动切换备用模型

会话策略：
- 429（配额耗尽）：任务内永久跳过该模型，因为配额窗口内无法恢复。
- 503（临时高峰）：仅跳过本次调用，下次请求仍从主模型重试，因为 503 是暂时性的。
新任务（plan/execute 开始时）调用 reset_session() 重置 429 记忆。
"""
import logging
from typing import List, Optional, Set

logger = logging.getLogger(__name__)

# 主模型 → 备用模型链（当主模型不可用时依次尝试）
MODEL_FALLBACK_CHAIN: List[str] = [
    "gemini-3.1-pro-preview",    # 主模型
    "gemini-3-pro-preview",      # 备用 1：3.0 Pro
    "gemini-3-flash-preview",    # 备用 2：3.0 Flash
]

# 本任务内已确认 429（配额耗尽）的模型，后续所有调用直接跳过
_session_exhausted_models: Set[str] = set()


def reset_session():
    """新任务开始时调用，重置 429 记忆，下个任务重新从主模型尝试"""
    global _session_exhausted_models
    if _session_exhausted_models:
        logger.info(f"🔄 新任务开始，重置模型选择（上一任务耗尽的模型: {_session_exhausted_models}）")
    _session_exhausted_models.clear()


def _is_quota_exhausted(e: Exception) -> bool:
    """429 配额耗尽：任务内应永久跳过该模型"""
    err_str = str(e).lower()
    if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
        return True
    for attr in ("status_code",):
        if getattr(e, attr, None) == 429:
            return True
    if hasattr(e, "response") and getattr(e.response, "status_code", None) == 429:
        return True
    return False


def _is_transient_unavailable(e: Exception) -> bool:
    """503 临时高峰：本次跳过，下次仍可重试主模型"""
    err_str = str(e).lower()
    if "503" in err_str or "unavailable" in err_str or "high demand" in err_str:
        return True
    for attr in ("status_code",):
        if getattr(e, attr, None) == 503:
            return True
    if hasattr(e, "response") and getattr(e.response, "status_code", None) == 503:
        return True
    return False


def _is_quota_exceeded(e: Exception) -> bool:
    """兼容旧调用"""
    return _is_quota_exhausted(e) or _is_transient_unavailable(e)


def chat_completion_with_fallback(
    client,
    model: Optional[str] = None,
    model_fallback: Optional[List[str]] = None,
    **kwargs,
):
    """
    调用 chat.completions.create，遇 429 或 503 时自动切换备用模型。

    - 429（配额耗尽）：本模型加入 session 黑名单，任务内后续调用直接跳过。
    - 503（临时高峰）：本次跳过，不加黑名单，下次调用仍先尝试主模型。

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

    # 跳过本任务内已确认 429 耗尽的模型（503 不在此列，可重试）
    effective_models = [m for m in models if m not in _session_exhausted_models]
    if not effective_models:
        raise RuntimeError("所有备用模型均已在本次任务中因配额耗尽被跳过，请新开任务重试")

    last_error = None
    for i, m in enumerate(effective_models):
        try:
            resp = client.chat.completions.create(model=m, **kwargs)
            if i > 0:
                logger.info(f"✅ 使用备用模型 {m} 完成调用")
            return resp
        except Exception as e:
            last_error = e
            if _is_quota_exhausted(e):
                # 429：永久加入黑名单
                _session_exhausted_models.add(m)
                if i < len(effective_models) - 1:
                    logger.warning(f"⚠️ 模型 {m} 配额耗尽 (429)，本任务后续跳过，切换到: {effective_models[i + 1]}")
                else:
                    raise
            elif _is_transient_unavailable(e):
                # 503：仅跳过本次，不加黑名单
                if i < len(effective_models) - 1:
                    logger.warning(f"⚠️ 模型 {m} 临时高峰 (503)，本次切换到: {effective_models[i + 1]}（下次仍会重试主模型）")
                else:
                    raise
            else:
                raise

    if last_error:
        raise last_error
