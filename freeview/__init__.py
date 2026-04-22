"""freeview package initialization.

Configure a package logger with a NullHandler so library logs don't
propagate unless the application configures logging.
"""
import logging

logger = logging.getLogger("freeview")
logger.addHandler(logging.NullHandler())

__all__ = ["logger"]
