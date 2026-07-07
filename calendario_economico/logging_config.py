"""configura logging. nivel via settings.log_level."""

import logging


def setup_logging(level: str = "INFO") -> None:
    """basicConfig. chamada uma vez no main()."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )