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
import threading

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
from src.api.talenta import get_attendance_status, get_tomorrow_shift, get_today_shift, is_work_day
from src.api.server import get_automation_state
from src.core import auth, location
from src.core.logger import setup_logger
from src.core.telegram import send_telegram_message
from src.config import config_local

# Initialize logger
logger = setup_logger('talenta_scheduler')

# Set timezone to Asia/Jakarta (GMT+7)
TIMEZONE = ZoneInfo(config_local.TIMEZONE)

# Module-level notification tracker to prevent duplicate notifications
# Format: {date_str: {'clock_in_skipped': bool, 'clock_out_skipped': bool}}
notification_tracker = {}


def check_and_notify_tomorrow_shift():
    """
    Check tomorrow's shift and send Telegram notification if WFO.
    Called after successful clock out.

    Shift types:
    - WFA: Work From Anywhere (no notification needed, auto clock in/out)
    - WFO: Work From Office (send notification)
    - dayoff/National Holiday/Company Holiday: Day off (no clock in/out needed)
    """
    try:
        shift_info = get_tomorrow_shift()

        if not shift_info:
            logger.warning("Could not fetch tomorrow's shift info")
            return

        office_hour = shift_info.get('office_hour_name', '')
        schedule_date = shift_info.get('schedule_date', '')
        is_holiday = shift_info.get('holiday', False)

        logger.info(f"📅 Tomorrow's shift ({schedule_date}): {office_hour}")

        # Determine shift type and action
        office_hour_lower = office_hour.lower() if office_hour else ''

        if 'wfo' in office_hour_lower:
            # WFO - Send notification to remind user to go to office
            message = (
                "🏢 WFO Reminder\n\n"
                f"Tomorrow ({schedule_date}) is a Work From Office day.\n"
                "Don't forget to go to the office!"
            )
            send_telegram_message(message)
            logger.info("📬 Sent WFO reminder notification")

        elif 'wfa' in office_hour_lower:
            # WFA - No notification needed, auto clock in/out will work
            logger.info("🏠 Tomorrow is WFA - automation will handle clock in/out")

        else:
            # Day off, holiday, or other - notify that no clock in/out is needed
            if is_holiday or office_hour_lower in ['dayoff', 'national holiday', 'company holiday']:
                message = (
                    "🎉 Day Off Tomorrow\n\n"
                    f"Tomorrow ({schedule_date}) is: {office_hour}\n"
                    "No clock in/out needed. Enjoy your day off!"
                )
                send_telegram_message(message)
                logger.info(f"📬 Sent day off notification: {office_hour}")
            else:
                # Unknown shift type - log warning
                logger.warning(f"Unknown shift type: {office_hour}")

    except Exception as error:
        logger.error(f"Error checking tomorrow's shift: {error}")


def start_flask_server():
    """
    Start Flask web server using Gunicorn (production WSGI server)
    Runs the control API on port from environment variable (default: 5000)
    """
    try:
        # Get port from environment variable (Railway, Heroku, etc.) or default to 5000
        port = int(os.environ.get('PORT', 5000))
        logger.info(f'🚀 Starting Flask control server with Gunicorn on port {port}...')

        # Use Gunicorn as production WSGI server
        # Run with:
        # - 1 worker (sufficient for this use case, more efficient)
        # - gevent worker class for better concurrency
        # - Bind to 0.0.0.0 to accept connections from any IP
        # - Access log disabled for cleaner output (app has its own logging)
        import subprocess
        subprocess.run([
            'gunicorn',
            '--workers', '1',
            '--worker-class', 'sync',  # sync is fine for low-traffic API
            '--bind', f'0.0.0.0:{port}',
            '--timeout', '30',  # Increase timeout to 120s for slow API calls
            '--access-logfile', '-',  # Log to stdout
            '--error-logfile', '-',   # Log to stdout
            '--log-level', 'info',
            'src.api.server:app'
        ])
    except Exception as error:
        logger.error(f'❌ Flask server error: {error}')

def clock_in_job(loc, cookies):
    """Job function for clocking in"""
    max_retries = 3
    attempt = 0
    current_cookies = cookies
    today_date = datetime.now(TIMEZONE).strftime('%Y-%m-%d')

    # Check if today's shift is WFA (only auto clock in for WFA, not WFO)
    today_shift = get_today_shift()
    if today_shift:
        office_hour = today_shift.get('office_hour_name', 'Unknown')
        is_holiday = today_shift.get('holiday', False)
        office_hour_lower = office_hour.lower() if office_hour else ''

        # Only proceed if it's WFA and not a holiday
        if 'wfa' not in office_hour_lower or is_holiday:
            logger.info(f'⏭️  Clock in skipped - today is {office_hour} (auto clock in only works for WFA)')
            return

    # Check if already clocked in before attempting
    try:
        attendance_status = get_attendance_status(current_cookies)

        # Skip if already clocked in
        if attendance_status['has_clocked_in']:
            # Check if notification already sent today
            if not notification_tracker.get(today_date, {}).get('clock_in_skipped', False):
                current_time = datetime.now(TIMEZONE)
                logger.info('⏭️  Clock in skipped - already clocked in today')

                # Send Telegram notification
                message = (
                    "🔔 Talenta Automation Alert\n\n"
                    "Clock In Skipped\n"
                    f"Date: {current_time.strftime('%Y-%m-%d')}\n"
                    f"Time: {current_time.strftime('%H:%M:%S %Z')}\n"
                    "Reason: You have already clocked in today."
                )
                send_telegram_message(message)

                # Mark notification as sent
                if today_date not in notification_tracker:
                    notification_tracker[today_date] = {'clock_in_skipped': True, 'clock_out_skipped': False}
                else:
                    notification_tracker[today_date]['clock_in_skipped'] = True
            else:
                logger.info('⏭️  Clock in skipped - already clocked in today (notification already sent)')

            return
    except Exception as status_error:
        logger.warning(f'⚠️  Failed to check attendance status: {status_error}')
        logger.info('🔄 Proceeding with clock in attempt...')

    # Check if automation is enabled
    if not get_automation_state():
        logger.info('⏸️  Clock in skipped - automation is disabled')
        return

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
                desc="ci"
            )

            # Display result
            if isinstance(result, dict):
                # logger.info(json.dumps(result, indent=2))
                # Only print success if status is 200
                if result.get('status') == 200:
                    logger.info('✅ Clock in successful!')
            else:
                # logger.info(result)
                logger.info('✅ Clock in successful!')

            return  # Exit after successful call

        except Exception as error:
            error_str = str(error)

            # Check if it's a 401 Unauthorized error
            if '401' in error_str and attempt < max_retries - 1:
                logger.warning(f'⚠️  Clock in failed with 401 Unauthorized')
                logger.info('🔐 Refreshing authentication cookies...')
                try:
                    current_cookies = auth.get_cookies()
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
    Hour: 5 PM (18:00)
    Minutes: Random between 10-30

    Returns:
        str: Time in HH:MM format (e.g., "18:23")
    """
    hour = 18
    minute = random.randint(10, 30)
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
    logger.info(f"   Clock in:  {clock_in_time} (randomized between 07:40-07:59)")
    logger.info(f"   Clock out: {clock_out_time} (randomized between 18:10-18:30)")
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
    today_date = datetime.now(TIMEZONE).strftime('%Y-%m-%d')

    # Check if today's shift is WFA (only auto clock out for WFA, not WFO)
    today_shift = get_today_shift()
    if today_shift:
        office_hour = today_shift.get('office_hour_name', 'Unknown')
        is_holiday = today_shift.get('holiday', False)
        office_hour_lower = office_hour.lower() if office_hour else ''

        # Only proceed if it's WFA and not a holiday
        if office_hour_lower != 'wfa' or is_holiday:
            logger.info(f'⏭️  Clock out skipped - today is {office_hour} (auto clock out only works for WFA)')
            # Still check tomorrow's shift even on off days
            check_and_notify_tomorrow_shift()
            return

    # Check if already clocked out before attempting
    try:
        attendance_status = get_attendance_status(current_cookies)

        # Skip if already clocked out
        if attendance_status['has_clocked_out']:
            # Check if notification already sent today
            if not notification_tracker.get(today_date, {}).get('clock_out_skipped', False):
                current_time = datetime.now(TIMEZONE)
                logger.info('⏭️  Clock out skipped - already clocked out today')

                # Send Telegram notification
                message = (
                    "🔔 Talenta Automation Alert\n\n"
                    "Clock Out Skipped\n"
                    f"Date: {current_time.strftime('%Y-%m-%d')}\n"
                    f"Time: {current_time.strftime('%H:%M:%S %Z')}\n"
                    "Reason: You have already clocked out today."
                )
                send_telegram_message(message)

                # Mark notification as sent
                if today_date not in notification_tracker:
                    notification_tracker[today_date] = {'clock_in_skipped': False, 'clock_out_skipped': True}
                else:
                    notification_tracker[today_date]['clock_out_skipped'] = True
            else:
                logger.info('⏭️  Clock out skipped - already clocked out today (notification already sent)')

            return
    except Exception as status_error:
        logger.warning(f'⚠️  Failed to check attendance status: {status_error}')
        logger.info('🔄 Proceeding with clock out attempt...')

    # Check if automation is enabled
    if not get_automation_state():
        logger.info('⏸️  Clock out skipped - automation is disabled')
        return

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
                desc="co"
            )

            # Display result
            if isinstance(result, dict):
                # logger.info(json.dumps(result, indent=2))
                # Only print success if status is 200
                if result.get('status') == 200:
                    logger.info('✅ Clock out successful!')
                    # Check tomorrow's shift and send notification
                    check_and_notify_tomorrow_shift()
            else:
                # logger.info(result)
                logger.info('✅ Clock out successful!')
                # Check tomorrow's shift and send notification
                check_and_notify_tomorrow_shift()

            return  # Exit after successful call

        except Exception as error:
            error_str = str(error)

            # Check if it's a 401 Unauthorized error
            if '401' in error_str and attempt < max_retries - 1:
                logger.warning(f'⚠️  Clock out failed with 401 Unauthorized')
                logger.info('🔐 Refreshing authentication cookies...')
                try:
                    current_cookies = auth.get_cookies()
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

        # Get cookies once at startup using shared auth function
        cookies = auth.get_cookies()
        logger.info('✅ Authentication configured successfully')
        logger.info("")

        # Schedule jobs with random times
        schedule_jobs_with_random_times(loc, cookies)

        # Start Flask server in background thread
        flask_thread = threading.Thread(
            target=start_flask_server,
            name='flask-server',
            daemon=True
        )
        flask_thread.start()
        time.sleep(1)  # Give Flask time to initialize

        # Get port for logging
        port = int(os.environ.get('PORT', 5000))

        logger.info("✅ Scheduler and web server started successfully!")
        logger.info(f"   Flask control server started on http://0.0.0.0:{port}")
        logger.info(f"   Web API available at http://localhost:{port} (use /enable, /disable, /status endpoints)")
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
