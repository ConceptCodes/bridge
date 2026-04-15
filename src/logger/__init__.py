from __future__ import annotations

import logging
import sys

APP_LOGGER_NAME = "bridge"
LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s"
)


class LoggerManager:
    _configured = False

    @classmethod
    def configure(cls, level: int = logging.INFO) -> logging.Logger:
        logger = logging.getLogger(APP_LOGGER_NAME)
        if cls._configured:
            return logger

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))

        logger.setLevel(level)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.propagate = False

        cls._configured = True
        return logger


def get_logger(name: str | None = None) -> logging.Logger:
    LoggerManager.configure()
    if name is None:
        return logging.getLogger(APP_LOGGER_NAME)
    return logging.getLogger(f"{APP_LOGGER_NAME}.{name}")


__all__ = [
    "APP_LOGGER_NAME",
    "LOG_FORMAT",
    "LoggerManager",
    "get_logger",
]
