"""
Logging configuration for Talenta scheduler
"""

import logging
import sys
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        import pytz
        def ZoneInfo(tz_name):
            return pytz.timezone(tz_name)
    except ImportError:
        from datetime import timezone, timedelta
        def ZoneInfo(tz_name):
            return timezone(timedelta(hours=7))


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[37m',      # White
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }

    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"

        return super().format(record)


def setup_logger(name='talenta_scheduler', level=logging.INFO, timezone='Asia/Jakarta'):
    """
    Setup and configure logger

    Args:
        name: Logger name
        level: Logging level (default: INFO)
        timezone: Timezone for timestamps (default: Asia/Jakarta)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Format: timestamp - level - message
    formatter = ColoredFormatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name='talenta_scheduler'):
    """
    Get existing logger instance

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
