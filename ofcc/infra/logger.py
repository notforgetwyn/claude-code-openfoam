import logging
import os
from pathlib import Path


def setup_logger(name: str = "ofcc", level: int = logging.INFO):
    log_dir = Path.home() / ".ofcc" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ofcc.log"

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(name)


def get_logger(name: str = "ofcc") -> logging.Logger:
    return logging.getLogger(name)
