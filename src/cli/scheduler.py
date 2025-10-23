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
import random
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

from src.api import talenta
from src.core import location
from src.core.logger import setup_logger
from src.config import config_local

# Initialize logger
logger = setup_logger('talenta_scheduler')

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
        logger.info('🔐 Using automatic authentication with email/password...')
        try:
            return talenta.fetch_cookies(config_local.EMAIL, config_local.PASSWORD)
        except Exception as error:
            logger.warning(f'⚠️  Automatic authentication failed: {error}')
            logger.info('🔄 Falling back to manual cookies...')

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


def clock_in_job(loc, cookies):
    """Job function for clocking in"""
    max_retries = 3
    attempt = 0
    current_cookies = cookies

    while attempt < max_retries:
        try:
            current_time = datetime.now(TIMEZONE)
            if attempt == 0:
                logger.info(f'\n⏰ Executing scheduled clock in...')
            else:
                logger.info(f'\n🔄 Retrying clock in (attempt {attempt + 1}/{max_retries})...')
            logger.info(f'   Time: {current_time.strftime("%Y-%m-%d %H:%M:%S %Z")}')

            result = talenta.clock_in(
                lat=loc['latitude'],
                long=loc['longitude'],
                cookies=current_cookies,
                desc="clock inn"
            )

            # Display result
            if isinstance(result, dict):
                logger.info(json.dumps(result, indent=2))
                # Only print success if status is 200
                if result.get('status') == 200:
                    logger.info('✅ Clock in successful!')
            else:
                logger.info(result)
                logger.info('✅ Clock in successful!')

            return  # Exit after successful call

        except Exception as error:
            error_str = str(error)

            # Check if it's a 401 Unauthorized error
            if '401' in error_str and attempt < max_retries - 1:
                logger.warning(f'⚠️  Clock in failed with 401 Unauthorized')
                logger.info('🔐 Refreshing authentication cookies...')
                try:
                    current_cookies = get_cookies()
                    logger.info('✅ Cookies refreshed successfully')
                    attempt += 1
                    continue  # Retry with new cookies
                except Exception as auth_error:
                    logger.error(f'❌ Failed to refresh cookies: {auth_error}')
                    return
            else:
                # Non-401 error or max retries reached
                logger.error(f'❌ Clock in failed: {error}')
                return


def generate_random_clock_in_time():
    """
    Generate random clock-in time
    Hour: 8 AM (08:00)
    Minutes: Random between 40-59

    Returns:
        str: Time in HH:MM format (e.g., "08:47")
    """
    hour = 8
    minute = random.randint(40, 59)
    return f"{hour:02d}:{minute:02d}"


def generate_random_clock_out_time():
    """
    Generate random clock-out time
    Hour: 6 PM (18:00)
    Minutes: Random between 00-59

    Returns:
        str: Time in HH:MM format (e.g., "18:23")
    """
    hour = 18
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"


def schedule_jobs_with_random_times(loc, cookies):
    """
    Schedule clock-in and clock-out jobs with randomized times
    Called at startup and daily at midnight to reschedule with new random times
    """
    # Clear existing jobs to reschedule with new times
    schedule.clear()

    # Generate random times for today
    clock_in_time = generate_random_clock_in_time()
    clock_out_time = generate_random_clock_out_time()

    # Log the scheduled times
    current_time = datetime.now(TIMEZONE)
    logger.info(f"🎲 Scheduling jobs with randomized times:")
    logger.info(f"   Date: {current_time.strftime('%Y-%m-%d')}")
    logger.info(f"   Clock in:  {clock_in_time} (randomized between 08:40-08:59)")
    logger.info(f"   Clock out: {clock_out_time} (randomized between 18:00-18:59)")
    logger.info("")

    # Schedule clock-in jobs for weekdays only (Monday-Friday)
    schedule.every().monday.at(clock_in_time).do(
        lambda: clock_in_job(loc, cookies)
    )
    schedule.every().tuesday.at(clock_in_time).do(
        lambda: clock_in_job(loc, cookies)
    )
    schedule.every().wednesday.at(clock_in_time).do(
        lambda: clock_in_job(loc, cookies)
    )
    schedule.every().thursday.at(clock_in_time).do(
        lambda: clock_in_job(loc, cookies)
    )
    schedule.every().friday.at(clock_in_time).do(
        lambda: clock_in_job(loc, cookies)
    )

    # Schedule clock-out jobs for weekdays only (Monday-Friday)
    schedule.every().monday.at(clock_out_time).do(
        lambda: clock_out_job(loc, cookies)
    )
    schedule.every().tuesday.at(clock_out_time).do(
        lambda: clock_out_job(loc, cookies)
    )
    schedule.every().wednesday.at(clock_out_time).do(
        lambda: clock_out_job(loc, cookies)
    )
    schedule.every().thursday.at(clock_out_time).do(
        lambda: clock_out_job(loc, cookies)
    )
    schedule.every().friday.at(clock_out_time).do(
        lambda: clock_out_job(loc, cookies)
    )

    # Schedule daily job at midnight to reschedule with new random times
    schedule.every().day.at("00:00").do(
        lambda: schedule_jobs_with_random_times(loc, cookies)
    )


def clock_out_job(loc, cookies):
    """Job function for clocking out"""
    max_retries = 3
    attempt = 0
    current_cookies = cookies

    while attempt < max_retries:
        try:
            current_time = datetime.now(TIMEZONE)
            if attempt == 0:
                logger.info(f'\n⏰ Executing scheduled clock out...')
            else:
                logger.info(f'\n🔄 Retrying clock out (attempt {attempt + 1}/{max_retries})...')
            logger.info(f'   Time: {current_time.strftime("%Y-%m-%d %H:%M:%S %Z")}')

            result = talenta.clock_out(
                lat=loc['latitude'],
                long=loc['longitude'],
                cookies=current_cookies,
                desc="clock outt"
            )

            # Display result
            if isinstance(result, dict):
                logger.info(json.dumps(result, indent=2))
                # Only print success if status is 200
                if result.get('status') == 200:
                    logger.info('✅ Clock out successful!')
            else:
                logger.info(result)
                logger.info('✅ Clock out successful!')

            return  # Exit after successful call

        except Exception as error:
            error_str = str(error)

            # Check if it's a 401 Unauthorized error
            if '401' in error_str and attempt < max_retries - 1:
                logger.warning(f'⚠️  Clock out failed with 401 Unauthorized')
                logger.info('🔐 Refreshing authentication cookies...')
                try:
                    current_cookies = get_cookies()
                    logger.info('✅ Cookies refreshed successfully')
                    attempt += 1
                    continue  # Retry with new cookies
                except Exception as auth_error:
                    logger.error(f'❌ Failed to refresh cookies: {auth_error}')
                    return
            else:
                # Non-401 error or max retries reached
                logger.error(f'❌ Clock out failed: {error}')
                return


def main():
    """Main scheduler function"""
    # Set system timezone
    os.environ['TZ'] = config_local.TIMEZONE
    if hasattr(time, 'tzset'):
        time.tzset()

    # Get current time in Asia/Jakarta timezone
    current_time = datetime.now(TIMEZONE)
    current_day = current_time.strftime('%A')

    logger.info(f"🕐 Starting scheduler with randomized times...")
    logger.info(f"   Timezone: {config_local.TIMEZONE} (GMT+7)")
    logger.info(f"   Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"   Current day: {current_day}")
    logger.info(f"   Clock in:  Randomized between 08:40-08:59 (Mon-Fri)")
    logger.info(f"   Clock out: Randomized between 18:00-18:59 (Mon-Fri)")
    logger.info("")

    try:
        # Get location once at startup
        config_dict = {
            'latitude': config_local.LATITUDE,
            'longitude': config_local.LONGITUDE
        }
        loc = location.get_location(config_dict)
        logger.info(f"📍 Using location: {loc['latitude']}, {loc['longitude']}")

        # Get cookies once at startup
        cookies = get_cookies()
        logger.info('✅ Authentication configured successfully')
        logger.info("")

        # Schedule jobs with random times
        schedule_jobs_with_random_times(loc, cookies)

        logger.info("✅ Scheduler started successfully!")
        logger.info("   Jobs will be rescheduled daily at midnight with new random times")
        logger.info("   Press Ctrl+C to stop")
        logger.info("")

        # Run the scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logger.info("\n\n🛑 Scheduler stopped by user")
    except Exception as error:
        logger.error(f"\n❌ Scheduler error: {error}")
        raise


if __name__ == '__main__':
    main()
