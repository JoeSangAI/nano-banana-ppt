"""
执行失败分类器
对 PPT 生成过程中的失败进行分类，并提供处理策略
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List


class FailureType(Enum):
    """失败类型枚举"""
    MATERIAL = "material"  # 素材问题（图片路径不存在、格式错误等）
    GENERATION = "generation"  # 生成问题（API 调用失败、超时等）
    PLAN = "plan"  # 计划问题（JSON 格式错误、字段缺失等）
    ASSEMBLY = "assembly"  # 组装问题（PPTX 创建失败、模板问题等）


class FailureSeverity(Enum):
    """失败严重程度"""
    TRANSIENT = "transient"  # 暂时性失败，可以重试
    PERMANENT = "permanent"  # 永久性失败，需要人工介入


@dataclass
class FailureReport:
    """失败报告"""
    failure_type: FailureType
    severity: FailureSeverity
    page_number: Optional[int] = None
    image_path: Optional[str] = None
    file_path: Optional[str] = None
    stage: Optional[str] = None  # 失败阶段：seed/parallel/assembly
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3
    can_retry: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "failure_type": self.failure_type.value,
            "severity": self.severity.value,
            "page_number": self.page_number,
            "image_path": self.image_path,
            "file_path": self.file_path,
            "stage": self.stage,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "can_retry": self.can_retry
        }


def classify_failure(
    exception: Exception,
    context: Dict[str, Any]
) -> FailureReport:
    """
    分类失败并生成报告

    Args:
        exception: 捕获的异常
        context: 上下文信息，包含：
            - page_number: 页码
            - image_path: 图片路径
            - file_path: 文件路径
            - stage: 执行阶段
            - retry_count: 已重试次数

    Returns:
        FailureReport: 失败报告
    """
    error_msg = str(exception)
    error_type = type(exception).__name__

    page_number = context.get("page_number")
    image_path = context.get("image_path")
    file_path = context.get("file_path")
    stage = context.get("stage", "unknown")
    retry_count = context.get("retry_count", 0)

    # 1. 素材问题检测
    if _is_material_failure(exception, error_msg):
        return FailureReport(
            failure_type=FailureType.MATERIAL,
            severity=FailureSeverity.PERMANENT,
            page_number=page_number,
            image_path=image_path,
            file_path=file_path,
            stage=stage,
            error_message=f"素材错误: {error_msg}",
            retry_count=retry_count,
            can_retry=False
        )

    # 2. 生成问题检测
    if _is_generation_failure(exception, error_msg):
        # 判断是否为暂时性失败
        is_transient = _is_transient_error(error_msg)
        return FailureReport(
            failure_type=FailureType.GENERATION,
            severity=FailureSeverity.TRANSIENT if is_transient else FailureSeverity.PERMANENT,
            page_number=page_number,
            image_path=image_path,
            file_path=file_path,
            stage=stage,
            error_message=f"生成错误: {error_msg}",
            retry_count=retry_count,
            can_retry=is_transient and retry_count < 3
        )

    # 3. 计划问题检测
    if _is_plan_failure(exception, error_msg):
        return FailureReport(
            failure_type=FailureType.PLAN,
            severity=FailureSeverity.PERMANENT,
            page_number=page_number,
            image_path=image_path,
            file_path=file_path,
            stage=stage,
            error_message=f"计划错误: {error_msg}",
            retry_count=retry_count,
            can_retry=False
        )

    # 4. 组装问题检测
    if _is_assembly_failure(exception, error_msg):
        return FailureReport(
            failure_type=FailureType.ASSEMBLY,
            severity=FailureSeverity.PERMANENT,
            page_number=page_number,
            image_path=image_path,
            file_path=file_path,
            stage=stage,
            error_message=f"组装错误: {error_msg}",
            retry_count=retry_count,
            can_retry=False
        )

    # 5. 默认：未知错误，视为暂时性生成问题
    return FailureReport(
        failure_type=FailureType.GENERATION,
        severity=FailureSeverity.TRANSIENT,
        page_number=page_number,
        image_path=image_path,
        file_path=file_path,
        stage=stage,
        error_message=f"未知错误 ({error_type}): {error_msg}",
        retry_count=retry_count,
        can_retry=retry_count < 3
    )


def _is_material_failure(exception: Exception, error_msg: str) -> bool:
    """判断是否为素材问题"""
    material_keywords = [
        "No such file",
        "cannot identify image file",
        "file not found",
        "FileNotFoundError",
        "does not exist",
        "invalid image",
        "cannot open",
        "Permission denied"
    ]

    error_type = type(exception).__name__
    if error_type in ["FileNotFoundError", "PermissionError", "OSError"]:
        return True

    return any(keyword.lower() in error_msg.lower() for keyword in material_keywords)


def _is_generation_failure(exception: Exception, error_msg: str) -> bool:
    """判断是否为生成问题"""
    generation_keywords = [
        "API",
        "timeout",
        "rate limit",
        "connection",
        "network",
        "HTTP",
        "status code",
        "request failed",
        "service unavailable",
        "bad gateway",
        "gateway timeout"
    ]

    error_type = type(exception).__name__
    if error_type in ["TimeoutError", "ConnectionError", "HTTPError", "RequestException"]:
        return True

    return any(keyword.lower() in error_msg.lower() for keyword in generation_keywords)


def _is_plan_failure(exception: Exception, error_msg: str) -> bool:
    """判断是否为计划问题"""
    plan_keywords = [
        "JSON",
        "KeyError",
        "missing required field",
        "invalid format",
        "parse error",
        "decode error",
        "schema validation"
    ]

    error_type = type(exception).__name__
    if error_type in ["JSONDecodeError", "KeyError", "ValueError", "TypeError"]:
        return True

    return any(keyword.lower() in error_msg.lower() for keyword in plan_keywords)


def _is_assembly_failure(exception: Exception, error_msg: str) -> bool:
    """判断是否为组装问题"""
    assembly_keywords = [
        "pptx",
        "presentation",
        "template",
        "slide layout",
        "PackageNotFoundError"
    ]

    return any(keyword.lower() in error_msg.lower() for keyword in assembly_keywords)


def _is_transient_error(error_msg: str) -> bool:
    """判断是否为暂时性错误（可重试）"""
    transient_keywords = [
        "timeout",
        "rate limit",
        "429",
        "503",
        "504",
        "connection reset",
        "temporary",
        "try again"
    ]

    return any(keyword.lower() in error_msg.lower() for keyword in transient_keywords)


def generate_failure_summary(failures: List[FailureReport]) -> str:
    """
    生成失败摘要报告

    Args:
        failures: 失败报告列表

    Returns:
        str: 格式化的摘要报告
    """
    if not failures:
        return "✅ 所有页面生成成功"

    # 按类型分组
    by_type: Dict[FailureType, List[FailureReport]] = {}
    for f in failures:
        if f.failure_type not in by_type:
            by_type[f.failure_type] = []
        by_type[f.failure_type].append(f)

    lines = [f"\n❌ 生成失败摘要（共 {len(failures)} 个失败）\n"]

    for failure_type, reports in by_type.items():
        lines.append(f"【{failure_type.value.upper()}】{len(reports)} 个失败:")
        for r in reports:
            page_info = f"第 {r.page_number} 页" if r.page_number else "未知页"
            stage_info = f"[{r.stage}]" if r.stage else ""
            lines.append(f"  - {page_info} {stage_info}: {r.error_message}")

    # 统计可重试和不可重试的失败
    retryable = [f for f in failures if f.can_retry]
    permanent = [f for f in failures if not f.can_retry]

    lines.append(f"\n📊 统计:")
    lines.append(f"  - 可重试: {len(retryable)} 个")
    lines.append(f"  - 需人工处理: {len(permanent)} 个")

    if permanent:
        pages = [str(f.page_number) for f in permanent if f.page_number]
        if pages:
            lines.append(f"  - 受影响页面: {', '.join(pages)}")

    return "\n".join(lines)
