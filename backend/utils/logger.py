"""Centralized logger with rotation."""
import logging
from logging.handlers import RotatingFileHandler
from backend.config import Config


_loggers = {}


def get_logger(name: str = "offsec") -> logging.Logger:
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))
    logger.propagate = False

    if not logger.handlers:
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            "%H:%M:%S"
        )
        # Console
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        # File (rotating)
        fh = RotatingFileHandler(
            Config.LOG_DIR / f"{name}.log",
            maxBytes=5_000_000, backupCount=5,
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    _loggers[name] = logger
    return logger
