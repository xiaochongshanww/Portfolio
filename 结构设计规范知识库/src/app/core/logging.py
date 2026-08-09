import json
import logging
from datetime import UTC, datetime
from typing import Any

from .config import settings
from .request_context import current_request_id

RESERVED_FIELDS = {"timestamp", "level", "logger", "event", "request_id", "exception"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        request_id = current_request_id()
        if request_id:
            payload["request_id"] = request_id
        extra = getattr(record, "extra_data", None)
        if isinstance(extra, dict):
            for key, value in extra.items():
                if key not in RESERVED_FIELDS:
                    payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str, separators=(",", ":"))


class ContextTextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        details: dict[str, Any] = {}
        request_id = current_request_id()
        if request_id:
            details["request_id"] = request_id
        extra = getattr(record, "extra_data", None)
        if isinstance(extra, dict):
            details.update(extra)
        return (
            f"{rendered} {json.dumps(details, ensure_ascii=False, default=str)}"
            if details
            else rendered
        )


def configure_logging() -> None:
    handler = logging.StreamHandler()
    formatter: logging.Formatter
    if settings.log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = ContextTextFormatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level, logging.INFO))
