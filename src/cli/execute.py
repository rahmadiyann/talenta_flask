#!/usr/bin/env python3
"""
CLI executor for Talenta clock in/out
Usage: python execute.py clockin|clockout
"""

import sys
import json
from datetime import datetime
from src.api import talenta
from src.api.talenta import get_attendance_status
from src.core import location
from src.core.logger import setup_logger
from src.core.telegram import send_telegram_message
from src.config import config_local

# Import timezone handling (zoneinfo for Python 3.9+, fallback to pytz)
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9
    try:
        import pytz
        # Use pytz timezone directly for compatibility
        def ZoneInfo(tz_name):
            return pytz.timezone(tz_name)
    except ImportError:
        # If pytz is also not available, use simple timezone
        from datetime import timezone, timedelta
        # Default to GMT+7 for Asia/Jakarta
        def ZoneInfo(tz_name):
            return timezone(timedelta(hours=7))

logger = setup_logger("talenta_executor")

def get_cookies():
    """
    Get authentication cookies (automatic or manual)

    Returns:
        Cookie string

    Raises:
        Exception: If authentication fails
    """
    # Check if email and password are provided for automatic authentication
    if config_local.EMAIL and config_local.PASSWORD:
        logger.info('🔐 Using automatic authentication with email/password...')
        try:
            return talenta.fetch_cookies(config_local.EMAIL, config_local.PASSWORD)
        except Exception as error:
            logger.warning(f'⚠️  Automatic authentication failed: {error}')
            logger.warning('🔄 Falling back to manual cookies...')

            if not config_local.COOKIES_TALENTA or config_local.COOKIES_TALENTA == 'PHPSESSID=<value>':
                raise Exception(
                    'Manual cookies not configured. Please set either EMAIL/PASSWORD or COOKIES_TALENTA in config.py'
                )
            return config_local.COOKIES_TALENTA

    # Fallback to manual cookies
    if not config_local.COOKIES_TALENTA or config_local.COOKIES_TALENTA == 'PHPSESSID=<value>':
        raise Exception(
            'Authentication not configured. Please set either:\n'
            '1. EMAIL and PASSWORD for automatic authentication, OR\n'
            '2. COOKIES_TALENTA for manual cookie authentication\n'
            'Check config.py for examples.'
        )

    logger.info('🍪 Using manual cookie authentication...')
    return config_local.COOKIES_TALENTA


def main():
    """Main execution function"""
    if len(sys.argv) < 2:
        logger.info("Usage: python execute.py clockin|clockout")
        sys.exit(1)

    action = sys.argv[1].lower()

    if action not in ['clockin', 'clockout']:
        logger.error("Error: Action must be 'clockin' or 'clockout'")
        sys.exit(1)

    try:
        # Get location (auto-detect or fallback to config)
        config_dict = {
            'latitude': config_local.LATITUDE,
            'longitude': config_local.LONGITUDE
        }
        loc = location.get_location(config_dict)

        # Get cookies (automatic or manual)
        cookies = get_cookies()

        # Check current attendance status
        TIMEZONE = ZoneInfo(config_local.TIMEZONE)
        attendance_status = get_attendance_status(cookies)

        # Execute the requested action
        if action == 'clockin':
            # Check if already clocked in
            if attendance_status['has_clocked_in']:
                current_time = datetime.now(TIMEZONE)
                logger.warning('⚠️  You have already clocked in today')

                # Send Telegram notification
                message = (
                    "🔔 Talenta Manual Operation Alert\n\n"
                    "Clock In Skipped\n"
                    f"Date: {current_time.strftime('%Y-%m-%d')}\n"
                    f"Time: {current_time.strftime('%H:%M:%S %Z')}\n"
                    "Reason: You have already clocked in today. Please check your attendance records."
                )
                send_telegram_message(message)
                sys.exit(0)
            logger.info('⏰ Clocking in...')
            result = talenta.clock_in(
                lat=loc['latitude'],
                long=loc['longitude'],
                cookies=cookies,
                desc="Hello I am In"
            )
        else:  # clockout
            # Check if already clocked out
            if attendance_status['has_clocked_out']:
                current_time = datetime.now(TIMEZONE)
                logger.warning('⚠️  You have already clocked out today')

                # Send Telegram notification
                message = (
                    "🔔 Talenta Manual Operation Alert\n\n"
                    "Clock Out Skipped\n"
                    f"Date: {current_time.strftime('%Y-%m-%d')}\n"
                    f"Time: {current_time.strftime('%H:%M:%S %Z')}\n"
                    "Reason: You have already clocked out today. Please check your attendance records."
                )
                send_telegram_message(message)
                sys.exit(0)
            logger.info('⏰ Clocking out...')
            result = talenta.clock_out(
                lat=loc['latitude'],
                long=loc['longitude'],
                cookies=cookies,
                desc="Goodbye I am Out"
            )

        # Display result
        logger.info('\n✅ Success!')
        if isinstance(result, dict):
            logger.info(json.dumps(result, indent=2))
        else:
            logger.info(result)

    except Exception as error:
        logger.error(f'\n❌ Error: {error}')
        sys.exit(1)


if __name__ == '__main__':
    main()
