#!/usr/bin/env python3
"""
Automated scheduler for Talenta clock in/out
Uses schedule library for cron-like scheduling
Timezone: Asia/Jakarta (GMT+7)
"""

import os
import time
import schedule
import json
from datetime import datetime

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

import talenta_api
import location

try:
    import config_local as config_local
except ImportError:
    import talenta_flask.config_local as config_local

# Set timezone to Asia/Jakarta (GMT+7)
TIMEZONE = ZoneInfo(config_local.TIMEZONE)


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
        print('🔐 Using automatic authentication with email/password...')
        try:
            return talenta_api.fetch_cookies(config_local.EMAIL, config_local.PASSWORD)
        except Exception as error:
            print(f'⚠️  Automatic authentication failed: {error}')
            print('🔄 Falling back to manual cookies...')

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

    print('🍪 Using manual cookie authentication...')
    return config_local.COOKIES_TALENTA


def clock_in_job(loc, cookies):
    """Job function for clocking in"""
    try:
        current_time = datetime.now(TIMEZONE)
        print(f'\n⏰ Executing scheduled clock in...')
        print(f'   Time: {current_time.strftime("%Y-%m-%d %H:%M:%S %Z")}')
        result = talenta_api.clock_in(
            lat=loc['latitude'],
            long=loc['longitude'],
            cookies=cookies,
            desc="Hello I am In"
        )
        print('✅ Clock in successful!')
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(result)
    except Exception as error:
        print(f'❌ Clock in failed: {error}')


def clock_out_job(loc, cookies):
    """Job function for clocking out"""
    try:
        current_time = datetime.now(TIMEZONE)
        print(f'\n⏰ Executing scheduled clock out...')
        print(f'   Time: {current_time.strftime("%Y-%m-%d %H:%M:%S %Z")}')
        result = talenta_api.clock_out(
            lat=loc['latitude'],
            long=loc['longitude'],
            cookies=cookies,
            desc="Goodbye I am Out"
        )
        print('✅ Clock out successful!')
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(result)
    except Exception as error:
        print(f'❌ Clock out failed: {error}')


def main():
    """Main scheduler function"""
    # Set system timezone
    os.environ['TZ'] = config_local.TIMEZONE
    if hasattr(time, 'tzset'):
        time.tzset()

    # Validate configuration
    if not config_local.TIME_CLOCK_IN or not config_local.TIME_CLOCK_OUT:
        print("✖︎ Error: TIME_CLOCK_IN and TIME_CLOCK_OUT must be defined in config.py")
        return

    # Get current time in Asia/Jakarta timezone
    current_time = datetime.now(TIMEZONE)
    current_day = current_time.strftime('%A')

    print(f"🕐 Starting scheduler...")
    print(f"   Timezone: {config_local.TIMEZONE} (GMT+7)")
    print(f"   Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   Current day: {current_day}")
    print(f"   Clock in scheduled for:  {config_local.TIME_CLOCK_IN} (Mon-Fri)")
    print(f"   Clock out scheduled for: {config_local.TIME_CLOCK_OUT} (Mon-Fri)")
    print()

    try:
        # Get location once at startup
        config_dict = {
            'latitude': config_local.LATITUDE,
            'longitude': config_local.LONGITUDE
        }
        loc = location.get_location(config_dict)
        print(f"📍 Using location: {loc['latitude']}, {loc['longitude']}")

        # Get cookies once at startup
        cookies = get_cookies()
        print('✅ Authentication configured successfully')
        print()

        # Schedule jobs for weekdays only (Monday-Friday)
        # Clock In
        schedule.every().monday.at(config_local.TIME_CLOCK_IN).do(
            lambda: clock_in_job(loc, cookies)
        )
        schedule.every().tuesday.at(config_local.TIME_CLOCK_IN).do(
            lambda: clock_in_job(loc, cookies)
        )
        schedule.every().wednesday.at(config_local.TIME_CLOCK_IN).do(
            lambda: clock_in_job(loc, cookies)
        )
        schedule.every().thursday.at(config_local.TIME_CLOCK_IN).do(
            lambda: clock_in_job(loc, cookies)
        )
        schedule.every().friday.at(config_local.TIME_CLOCK_IN).do(
            lambda: clock_in_job(loc, cookies)
        )

        # Clock Out
        schedule.every().monday.at(config_local.TIME_CLOCK_OUT).do(
            lambda: clock_out_job(loc, cookies)
        )
        schedule.every().tuesday.at(config_local.TIME_CLOCK_OUT).do(
            lambda: clock_out_job(loc, cookies)
        )
        schedule.every().wednesday.at(config_local.TIME_CLOCK_OUT).do(
            lambda: clock_out_job(loc, cookies)
        )
        schedule.every().thursday.at(config_local.TIME_CLOCK_OUT).do(
            lambda: clock_out_job(loc, cookies)
        )
        schedule.every().friday.at(config_local.TIME_CLOCK_OUT).do(
            lambda: clock_out_job(loc, cookies)
        )

        print("✅ Scheduler started successfully!")
        print("   Press Ctrl+C to stop")
        print()

        # Run the scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        print("\n\n🛑 Scheduler stopped by user")
    except Exception as error:
        print(f"\n❌ Scheduler error: {error}")
        raise


if __name__ == '__main__':
    main()
