"""项目日志初始化工具。"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core.models import get_settings
from core.utils.project_paths import OUTPUT_DIR, ensure_runtime_directories


def configure_logging(force: bool = False) -> Path:
    """初始化控制台 + 文件日志。"""
    settings = get_settings()
    ensure_runtime_directories()

    log_file = Path(settings.log_file) if settings.log_file else OUTPUT_DIR / "app.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers and not force:
        return log_file

    level_name = (settings.log_level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=level,
        handlers=[console_handler, file_handler],
        force=force,
    )

    logging.getLogger(__name__).info("Logging initialized: %s", log_file)
    return log_file
