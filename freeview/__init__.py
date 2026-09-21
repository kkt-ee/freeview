"""freeview — Interactive FreeSurfer Stats Dashboard.

Copyright (C) 2026 Kishore Kumar Tarafdar
SPDX-License-Identifier: GPL-3.0-or-later

See LICENSE for full license text.

Configure a package logger with a NullHandler so library logs don't
propagate unless the application configures logging.
"""

import logging


__author__ = "Kishore Kumar Tarafdar"
__version__ = "0.0.3"


logger = logging.getLogger("freeview")
logger.addHandler(logging.NullHandler())

__all__ = ["logger", "__version__", "__author__"]
