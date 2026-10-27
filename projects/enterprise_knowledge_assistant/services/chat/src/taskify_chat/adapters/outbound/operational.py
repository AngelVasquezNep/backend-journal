"""Configure only owned redacted operational logging; provider/root logging stays unchanged."""

import logging


def configure_logging() -> None:
    """Enable fixed-field taskify request/worker outcomes without activating third-party payload tracing."""
    logger = logging.getLogger("taskify")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
