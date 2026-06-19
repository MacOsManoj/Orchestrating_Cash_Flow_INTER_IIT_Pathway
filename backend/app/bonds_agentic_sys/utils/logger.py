"""
Centralized logging configuration for the bond pipeline
Provides structured logging with context support
"""

import logging
import sys
import os
from typing import Optional, Dict, Any
from pathlib import Path


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_dir: Optional[str] = None,
    log_to_file: bool = False,
) -> logging.Logger:
    """
    Setup a logger with console and optional file handlers

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
        log_dir: Directory for log files (default: logs/)
        log_to_file: Whether to log to file (default: False)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_to_file:
        if log_dir is None:
            log_dir = os.path.join(Path(__file__).parent.parent, "logs")
        os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"{name.replace('.', '_')}.log"), encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger instance

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Default logger for orchestrator
orchestrator_logger = setup_logger("orchestrator", log_to_file=False)
