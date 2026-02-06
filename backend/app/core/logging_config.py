import logging
import sys
from pathlib import Path

from app.config import settings


def setup_logging() -> None:
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )

    # 使用带 flush 的 StreamHandler，确保每条日志立即输出
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.flush = lambda: sys.stdout.flush()
    handlers: list[logging.Handler] = [stdout_handler]

    if settings.LOG_FILE:
        log_file = Path(settings.LOG_FILE)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,  # 强制重新配置，覆盖之前的 basicConfig
    )

    # 降低第三方库日志级别
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)

    logging.getLogger(__name__).info(
        "Logging configured: level=%s, log_file=%s",
        settings.LOG_LEVEL,
        settings.LOG_FILE or "(stdout only)",
    )
