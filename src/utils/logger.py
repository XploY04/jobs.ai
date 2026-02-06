import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """Configure and return an application logger."""

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "job_aggregator.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
