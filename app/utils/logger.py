"""Structured logging setup with console and file rotation support."""

import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from app.config import settings


def setup_logger(name: str = "kb_geoid") -> logging.Logger:
    """Configure and return a structured logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Formatter
    log_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # File Handler with rotation
    try:
        log_dir = settings.BASE_DIR / settings.LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=log_dir / "geoid_bot.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not create file log handler: {e}")

    return logger


logger = setup_logger()
