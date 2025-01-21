import os
import logging

logger = logging.getLogger(__name__)


REQUIRED_CONFIGS = [
    "SECRET_KEY",
]


def get_config(key, default=None):
    value = os.environ.get(key, default)
    if value is None and key in REQUIRED_CONFIGS:
        raise ValueError(f"Required config {key} is missing")
    return value
