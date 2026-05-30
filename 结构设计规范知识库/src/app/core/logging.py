import logging

from .config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

