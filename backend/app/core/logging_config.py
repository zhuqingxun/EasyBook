import logging
import sys
from pathlib import Path

from app.config import settings


def setup_logging() -> None:
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if settings.LOG_FILE:
        log_file = Path(settings.LOG_FILE)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )

    # 降低第三方库日志级别
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
