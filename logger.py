"""Logging configuration for Job Hunt OS.

Configures console and file handlers with timestamps and levels.
"""
from __future__ import annotations

import logging
import os
from logging import Logger
from typing import Optional


def setup_logger(name: str = "jobhunt", log_file: Optional[str] = None) -> Logger:
    """Configure and return a logger.

    Args:
        name: Logger name.
        log_file: Path for file logging. If provided ensures parent directory exists.

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(fmt)
        logger.addHandler(console)

        if log_file:
            directory = os.path.dirname(log_file)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(fmt)
            logger.addHandler(file_handler)

    return logger


__all__ = ["setup_logger"]
