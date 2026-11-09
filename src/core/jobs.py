"""
Account-aware clock in/out jobs.

This module holds the actual clock in/out logic so it can be shared by both the
background scheduler (automatic, time-triggered) and the web API (manual, button
triggered). Every attempt is written to the action log so the admin panel can
show recent activity.
"""

from datetime import datetime
from typing import Dict

from src.api import talenta
from src.api.talenta import (
    get_attendance_status,
    get_attendance_status_api,
    get_today_shift,
    get_tomorrow_shift,
)
from src.core import auth, accounts
from src.core.logger import get_logger
from src.core.telegram import send_telegram_message
from src.config import config_local

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - fallback for Python < 3.9
    try:
        import pytz

        def ZoneInfo(tz_name):
            return pytz.timezone(tz_name)
    except ImportError:
        from datetime import timedelta, timezone

        def ZoneInfo(tz_name):
            return timezone(timedelta(hours=7))

logger = get_logger('talenta_jobs')

TIMEZONE = ZoneInfo(config_local.TIMEZONE)

MAX_RETRIES = 3


def _now():
    return datetime.now(TIMEZONE)


def _loc(account: Dict) -> Dict[str, str]:
    return {
        'latitude': account.get('latitude') or config_local.LATITUDE,
        'longitude': account.get('longitude') or config_local.LONGITUDE,
    }


def _shift_allows(account: Dict, action: str) -> Dict:
    """
    Decide whether today's shift permits an automatic clock action.

    Returns a dict ``{'allowed': bool, 'reason': str, 'shift': str}``.

    - When ``wfa_only`` is set, only WFA days qualify (the original behaviour).
    - Otherwise both WFA and WFO count as work days.
    - Holidays and day-off never qualify.
    If the shift cannot be determined, we allow the action (fail open) so a
    schedule lookup problem never silently blocks attendance.
    """
    shift_info = get_today_shift(account=account)
    if not shift_info:
        return {'allowed': True, 'reason': 'shift unknown (proceeding)', 'shift': 'unknown'}

    office_hour = (shift_info.get('office_hour_name') or '').strip()
    office_hour_lower = office_hour.lower()
    is_holiday = shift_info.get('holiday', False)

    if is_holiday:
        return {'allowed': False, 'reason': f'holiday ({office_hour})', 'shift': office_hour}

    allowed_shifts = ['wfa'] if account.get('wfa_only') else ['wfa', 'wfo']
    if office_hour_lower in allowed_shifts:
        return {'allowed': True, 'reason': office_hour, 'shift': office_hour}

    return {'allowed': False, 'reason': f'{office_hour} not in {allowed_shifts}', 'shift': office_hour}


def _notify_tomorrow_shift(account: Dict) -> None:
    """After a clock out, remind the user about tomorrow's shift (WFO / day off)."""
    try:
        shift_info = get_tomorrow_shift(account=account)
        if not shift_info:
            return

        office_hour = shift_info.get('office_hour_name', '') or ''
        schedule_date = shift_info.get('schedule_date', '')
        is_holiday = shift_info.get('holiday', False)
        office_hour_lower = office_hour.lower()
        label = account.get('label', '')

        if 'wfo' in office_hour_lower:
            send_telegram_message(
                f"🏢 WFO Reminder ({label})\n\n"
                f"Tomorrow ({schedule_date}) is a Work From Office day.\n"
                "Don't forget to go to the office!",
                account=account,
            )
        elif 'wfa' in office_hour_lower:
            logger.info(f"🏠 [{label}] Tomorrow is WFA - automation will handle it")
        elif is_holiday or office_hour_lower in ['dayoff', 'national holiday', 'company holiday']:
            send_telegram_message(
                f"🎉 Day Off Tomorrow ({label})\n\n"
                f"Tomorrow ({schedule_date}) is: {office_hour}\n"
                "No clock in/out needed. Enjoy your day off!",
                account=account,
            )
    except Exception as error:
        logger.error(f"Error checking tomorrow's shift: {error}")


def _run_clock(account: Dict, action: str, trigger: str, force: bool = False) -> Dict:
    """
    Core clock in/out routine shared by in/out actions.

    Args:
        account: Account dict.
        action: 'clockin' or 'clockout'.
        trigger: 'auto' or 'manual' (for logging/notification wording).
        force: when True, skip the "already clocked today" guard and post anyway
            (used by a confirmed manual double clock in/out from the panel).

    Returns:
        Dict: {'success': bool, 'status': 'success'|'skipped'|'failed', 'message': str}
    """
    is_out = action == 'clockout'
    label = account.get('label', f"#{account.get('id')}")
    verb = 'Clock out' if is_out else 'Clock in'

    def done(status: str, message: str, success: bool) -> Dict:
        accounts.log_action(account, action, status, message, trigger)
        return {'success': success, 'status': status, 'message': message}

    # 1. Shift gating only applies to automatic runs; a manual press is explicit intent.
    if trigger == 'auto':
        gate = _shift_allows(account, action)
        if not gate['allowed']:
            logger.info(f"⏭️  [{label}] {verb} skipped - {gate['reason']}")
            if is_out:
                _notify_tomorrow_shift(account)
            return done('skipped', f"Skipped: {gate['reason']}", True)

    # 2. Authenticate.
    try:
        cookies = auth.get_cookies_for_account(account)
    except Exception as error:
        logger.error(f"❌ [{label}] Auth failed: {error}")
        send_telegram_message(
            f"🚨 Talenta {verb} Failed ({label})\n\n"
            f"Time: {_now().strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"Reason: Authentication failed\nError: {error}",
            account=account,
        )
        return done('failed', f'Authentication failed: {error}', False)

    # 3. Skip if already clocked for this action today, unless the caller forces
    #    a confirmed double clock. Prefer the reliable Mekari API; fall back to
    #    HTML scraping if needed.
    if force:
        logger.info(f"⚠️  [{label}] {verb} forced (double clock confirmed)")
    else:
        try:
            status = get_attendance_status_api(account=account)
            if status is None:
                status = get_attendance_status(cookies)
            already = status['has_clocked_out'] if is_out else status['has_clocked_in']
            if already:
                logger.info(f"⏭️  [{label}] {verb} skipped - already done today")
                send_telegram_message(
                    f"🔔 Talenta Alert ({label})\n\n{verb} Skipped\n"
                    f"Time: {_now().strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
                    f"Reason: Already {('clocked out' if is_out else 'clocked in')} today.",
                    account=account,
                )
                if is_out:
                    _notify_tomorrow_shift(account)
                return done('skipped', f'Already {("clocked out" if is_out else "clocked in")} today', True)
        except Exception as status_error:
            logger.warning(f"⚠️  [{label}] Could not check attendance status: {status_error}")

    # 4. Perform the clock action with cookie-refresh retry on 401.
    loc = _loc(account)
    attempt = 0
    current_cookies = cookies
    while attempt < MAX_RETRIES:
        try:
            if attempt:
                logger.info(f"🔄 [{label}] Retrying {verb.lower()} ({attempt + 1}/{MAX_RETRIES})...")
            else:
                logger.info(f"⏰ [{label}] Executing {verb.lower()}...")

            fn = talenta.clock_out if is_out else talenta.clock_in
            result = fn(
                lat=loc['latitude'],
                long=loc['longitude'],
                cookies=current_cookies,
                desc='co' if is_out else 'ci',
            )

            ok = (not isinstance(result, dict)) or result.get('status') == 200
            if ok:
                logger.info(f"✅ [{label}] {verb} successful!")
                if is_out:
                    _notify_tomorrow_shift(account)
                return done('success', f'{verb} successful', True)

            # dict result without status 200 -> treat as failure
            raise Exception(f'Unexpected response: {result}')

        except Exception as error:
            error_str = str(error)
            if '401' in error_str and attempt < MAX_RETRIES - 1:
                logger.warning(f"⚠️  [{label}] 401 Unauthorized - refreshing cookies...")
                try:
                    current_cookies = auth.get_cookies_for_account(account)
                    attempt += 1
                    continue
                except Exception as auth_error:
                    logger.error(f"❌ [{label}] Cookie refresh failed: {auth_error}")
                    send_telegram_message(
                        f"🚨 Talenta {verb} Failed ({label})\n\n"
                        f"Time: {_now().strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
                        f"Reason: Auth refresh failed\nError: {auth_error}",
                        account=account,
                    )
                    return done('failed', f'Auth refresh failed: {auth_error}', False)
            else:
                logger.error(f"❌ [{label}] {verb} failed: {error}")
                send_telegram_message(
                    f"🚨 Talenta {verb} Failed ({label})\n\n"
                    f"Time: {_now().strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
                    f"Attempts: {attempt + 1}/{MAX_RETRIES}\nError: {error}",
                    account=account,
                )
                return done('failed', str(error), False)

    return done('failed', 'Exhausted retries', False)


def clock_in_for_account(account: Dict, trigger: str = 'auto', force: bool = False) -> Dict:
    """Clock in for a single account. ``trigger`` is 'auto' or 'manual'."""
    return _run_clock(account, 'clockin', trigger, force=force)


def clock_out_for_account(account: Dict, trigger: str = 'auto', force: bool = False) -> Dict:
    """Clock out for a single account. ``trigger`` is 'auto' or 'manual'."""
    return _run_clock(account, 'clockout', trigger, force=force)
