"""Logging setup for the application."""

from __future__ import annotations

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """Configure basic logging for the CLI.

    Parameters
    ----------
    level:
        Logging level to use. Defaults to ``logging.INFO``.
    """

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
