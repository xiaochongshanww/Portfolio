"""构建流水线进度事件的轻量协议。"""

from collections.abc import Callable
from typing import Any

ProgressCallback = Callable[[str, str, dict[str, Any]], None]


def emit_progress(
    callback: ProgressCallback | None,
    stage: str,
    message: str,
    **details: Any,
) -> None:
    if callback is not None:
        callback(stage, message, details)
