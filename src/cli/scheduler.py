#!/usr/bin/env python3
"""
Multi-account automated scheduler for Talenta clock in/out.

Runs a minute-resolution tick loop that, for every enabled account, fires an
automatic clock in / clock out when the current time reaches that account's
configured target (with an optional per-account daily random jitter). Accounts
are read fresh from the database on every tick, so changes made in the admin
panel take effect without restarting the scheduler.

Timezone: configured via TZ (default Asia/Jakarta, GMT+7).
"""

import hashlib
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta

# Import timezone handling (zoneinfo for Python 3.9+, fallback to pytz)
try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        import pytz

        def ZoneInfo(tz_name):
            return pytz.timezone(tz_name)
    except ImportError:
        from datetime import timezone

        def ZoneInfo(tz_name):
            return timezone(timedelta(hours=7))

from src.core import accounts
from src.core.jobs import clock_in_for_account, clock_out_for_account
from src.core.logger import setup_logger
from src.config import config_local

logger = setup_logger('talenta_scheduler')

TIMEZONE = ZoneInfo(config_local.TIMEZONE)

# How long after a target time we may still fire the job (covers brief downtime /
# a missed tick without firing hours-late after a restart).
GRACE = timedelta(minutes=10)

# How often the loop wakes up to check targets.
TICK_SECONDS = 30


def _parse_hhmm(value: str, default: str) -> tuple:
    """Parse 'HH:MM' (also accepts 'HH.MM' / 'HHMM') into (hour, minute)."""
    raw = (value or default).strip().replace('.', ':')
    try:
        if ':' in raw:
            hh, mm = raw.split(':')
        elif raw.isdigit() and len(raw) in (3, 4):
            hh, mm = raw[:-2], raw[-2:]
        else:
            raise ValueError
        hour, minute = int(hh), int(mm)
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError
        return hour, minute
    except ValueError:
        logger.warning(f"Invalid time '{value}', using default {default}")
        hh, mm = default.split(':')
        return int(hh), int(mm)


def _daily_jitter(date_str: str, account_id, action: str, jitter_minutes: int) -> int:
    """
    Deterministic jitter (0..jitter_minutes) for a given day/account/action.

    Deterministic so the computed target is stable across every tick of the same
    day, yet varies between days and accounts.
    """
    if jitter_minutes <= 0:
        return 0
    key = f'{date_str}:{account_id}:{action}'.encode()
    digest = int(hashlib.md5(key).hexdigest(), 16)
    return digest % (jitter_minutes + 1)


def _target_time(now: datetime, date_str: str, account: dict, action: str) -> datetime:
    """Compute today's target datetime for a clock action, including jitter."""
    field = 'clock_out_time' if action == 'clockout' else 'clock_in_time'
    default = '18:15' if action == 'clockout' else '08:50'
    hour, minute = _parse_hhmm(account.get(field), default)
    base = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    offset = _daily_jitter(date_str, account.get('id'), action, int(account.get('jitter_minutes', 0) or 0))
    return base + timedelta(minutes=offset)


def start_flask_server():
    """Start the Flask control/admin server via Gunicorn in a subprocess."""
    try:
        port = int(os.environ.get('PORT', 5000))
        logger.info(f'🚀 Starting admin panel + control API (Gunicorn) on port {port}...')
        subprocess.run([
            'gunicorn',
            '--workers', '1',
            '--worker-class', 'sync',
            '--bind', f'0.0.0.0:{port}',
            '--timeout', '60',
            '--access-logfile', '-',
            '--error-logfile', '-',
            '--log-level', 'info',
            'src.api.server:app',
        ])
    except Exception as error:
        logger.error(f'❌ Flask server error: {error}')


def _tick(now: datetime, date_str: str, fired: dict) -> None:
    """Evaluate every enabled account once and fire any due clock actions."""
    try:
        all_accounts = accounts.list_accounts()
    except Exception as error:
        logger.error(f'Could not load accounts: {error}')
        return

    for account in all_accounts:
        if not account.get('enabled'):
            continue

        account_id = account.get('id')
        account_fired = fired.setdefault(account_id, {'clockin': False, 'clockout': False})

        for action, runner in (('clockin', clock_in_for_account),
                               ('clockout', clock_out_for_account)):
            if account_fired[action]:
                continue
            target = _target_time(now, date_str, account, action)
            if target <= now <= target + GRACE:
                account_fired[action] = True
                logger.info(
                    f"🎯 [{account.get('label')}] {action} due "
                    f"(target {target.strftime('%H:%M')}, now {now.strftime('%H:%M')})"
                )
                try:
                    runner(account, trigger='auto')
                except Exception as error:
                    logger.error(f"Job error for account #{account_id} {action}: {error}")


def main():
    """Main scheduler loop."""
    os.environ['TZ'] = config_local.TIMEZONE
    if hasattr(time, 'tzset'):
        time.tzset()

    # Prepare database and migrate any .env-configured account on first run.
    accounts.seed_from_env()

    now = datetime.now(TIMEZONE)
    logger.info('🕐 Starting multi-account Talenta scheduler...')
    logger.info(f'   Timezone: {config_local.TIMEZONE}')
    logger.info(f"   Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    try:
        account_list = accounts.list_accounts()
        logger.info(f'   Accounts loaded: {len(account_list)} '
                    f"({sum(1 for a in account_list if a['enabled'])} enabled)")
    except Exception as error:
        logger.error(f'Could not load accounts at startup: {error}')

    # Start the web server (admin panel + REST API) alongside the scheduler.
    flask_thread = threading.Thread(target=start_flask_server, name='flask-server', daemon=True)
    flask_thread.start()
    time.sleep(1)

    port = int(os.environ.get('PORT', 5000))
    logger.info(f'✅ Admin panel available at http://localhost:{port}')
    logger.info('   Clock in/out fire per-account at their configured times (Mon-Fri shifts).')
    logger.info('   Press Ctrl+C to stop.')
    logger.info('')

    current_day = None
    fired = {}

    try:
        while True:
            now = datetime.now(TIMEZONE)
            date_str = now.strftime('%Y-%m-%d')

            # Reset the "already fired today" tracking at the start of a new day.
            if date_str != current_day:
                current_day = date_str
                fired = {}
                logger.info(f'📅 New day: {date_str} - targets reset')

            # Only run attendance on weekdays; shift gating in jobs handles the rest.
            if now.weekday() < 5:
                _tick(now, date_str, fired)

            time.sleep(TICK_SECONDS)

    except KeyboardInterrupt:
        logger.info('\n\n🛑 Scheduler stopped by user')
    except Exception as error:
        logger.error(f'\n❌ Scheduler error: {error}')
        raise


if __name__ == '__main__':
    main()
