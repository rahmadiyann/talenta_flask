"""
Talenta API Module - Python Implementation
Main module for clocking in and out of Mekari Talenta HR system
"""

import base64
import codecs
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.core.auth import extract_authenticity_token, extract_cookies
from src.core.logger import setup_logger
from src.config.config_local import (
    TIMEZONE,
    MEKARI_BEARER_TOKEN,
    MEKARI_ORGANISATION_ID,
    MEKARI_ORGANISATION_USER_ID
)

logger = setup_logger("talenta_api")

# Timezone handling (same pattern as logger.py)
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

def rot13(text: str) -> str:
    """
    ROT13 encoding function

    Args:
        text: String to encode

    Returns:
        ROT13 encoded string
    """
    return codecs.encode(text, 'rot_13')


def encoder(value: str, encoding: str) -> str:
    """
    Multi-encoding wrapper

    Args:
        value: String to encode
        encoding: Encoding type ('base64' or 'rot13')

    Returns:
        Encoded string
    """
    if encoding == 'base64':
        return base64.b64encode(value.encode()).decode()
    elif encoding == 'rot13':
        return rot13(value)
    return value


def get_csrf_token(cookies: str) -> Optional[str]:
    """
    Fetch CSRF token from Talenta live-attendance page

    Args:
        cookies: Session cookie string

    Returns:
        CSRF token or None if not found
    """
    try:
        headers = {
            'Cookie': cookies,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }

        response = requests.get(
            'https://hr.talenta.co/live-attendance',
            headers=headers,
            timeout=10
        )

        if not response.ok:
            raise Exception(f"HTTP {response.status_code}: {response.reason}")

        html = response.text

        # Look for CSRF token in common patterns
        csrf_patterns = [
            r'name="csrf-token" content="([^"]+)"',
            r'name="_token" content="([^"]+)"',
            r'window\.Laravel\.csrfToken = "([^"]+)"',
            r'<meta name="csrf-token" content="([^"]+)"',
        ]

        for pattern in csrf_patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)

        return None

    except Exception as error:
        logger.error(f"⚠️  Could not fetch CSRF token: {error}")
        return None


def get_attendance_status(cookies: str) -> Dict[str, bool]:
    """
    Check if the user has already clocked in or out today.

    This function implements a two-tier approach:
    1. Primary: Attempts to fetch attendance data from the internal API endpoint
    2. Fallback: If API fails, parses the HTML page to extract attendance status

    Args:
        cookies: Session cookie string

    Returns:
        Dictionary with two boolean keys:
        - has_clocked_in: True if user has clocked in today
        - has_clocked_out: True if user has clocked out today

        Returns False values on uncertainty or errors (allowing automation to proceed).
    """
    # Default return value (safe default - allows automation to proceed)
    default_status = {'has_clocked_in': False, 'has_clocked_out': False}

    try:
        headers = {
            'Cookie': cookies,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }

        # Parse HTML page for atendance status
        logger.info('🔍 Parsing attendance status HTML...')

        try:
            html_response = requests.get(
                'https://hr.talenta.co/live-attendance',
                headers=headers,
                timeout=10
            )

            if html_response.status_code == 200:
                html = html_response.text

                # Parse attendance log section to check today's attendance
                # The attendance log contains entries like:
                # <div>08:49 AM</div>
                # <small>24 Oct</small>
                # <p>Clock In</p>

                has_clocked_in = False
                has_clocked_out = False

                # Get today's date in the format shown in attendance log (e.g., "24 Oct")
                try:
                    tz = ZoneInfo(TIMEZONE)
                except:
                    from datetime import timezone, timedelta
                    tz = timezone(timedelta(hours=7))

                today = datetime.now(tz)
                today_str = today.strftime('%d %b')  # Format: "24 Oct"

                # Pattern to find attendance log entries for today
                # Look for sections containing today's date followed by Clock In/Out

                # Split HTML by attendance log items (li elements)
                log_entries = re.findall(
                    r'<li[^>]*>.*?<div[^>]*>(\d{2}:\d{2}\s+(?:AM|PM))</div>.*?<small[^>]*>(.*?)</small>.*?<p[^>]*>(.*?)</p>',
                    html,
                    re.DOTALL | re.IGNORECASE
                )

                logger.info(f'📋 Found {len(log_entries)} attendance log entries')

                # Check each entry for today's date
                for time_str, date_str, action_str in log_entries:
                    # Clean up the strings
                    date_str = re.sub(r'\s+', ' ', date_str.strip())
                    action_str = re.sub(r'\s+', ' ', action_str.strip())

                    logger.info(f'   Entry: {date_str} - {time_str} - {action_str}')

                    # Check if this entry is from today
                    if today_str in date_str:
                        if 'Clock In' in action_str:
                            has_clocked_in = True
                            logger.info(f'   ✅ Found Clock In entry for today')
                        elif 'Clock Out' in action_str:
                            has_clocked_out = True
                            logger.info(f'   ✅ Found Clock Out entry for today')

                logger.info(f'✅ Attendance status from log: clocked_in={has_clocked_in}, clocked_out={has_clocked_out}')
                return {
                    'has_clocked_in': has_clocked_in,
                    'has_clocked_out': has_clocked_out
                }
            else:
                logger.error(f'⚠️  HTML page returned status {html_response.status_code}')
                return default_status

        except requests.exceptions.RequestException as html_error:
            logger.error(f'⚠️  HTML request failed: {html_error}')
            return default_status

    except Exception as error:
        logger.error(f'⚠️  Could not check attendance status: {error}')
        return default_status


def prep_form(lat: str, long: str, cookies: str, desc: str, is_checkout: bool = False) -> Dict[str, Any]:
    """
    Prepare form data and headers for attendance request

    Args:
        lat: Latitude coordinate
        long: Longitude coordinate
        cookies: Session cookie string
        desc: Description message
        is_checkout: True for checkout, False for checkin

    Returns:
        Dictionary with form data and headers
    """
    status = "checkout" if is_checkout else "checkin"

    # Double encode coordinates (Base64 -> ROT13)
    long_encoded = encoder(encoder(long, "base64"), "rot13")
    lat_encoded = encoder(encoder(lat, "base64"), "rot13")

    # Get CSRF token
    csrf_token = get_csrf_token(cookies)

    # Prepare form data
    data = {
        'longitude': long_encoded,
        'latitude': lat_encoded,
        'status': status,
        'description': desc,
    }

    if csrf_token:
        data['_token'] = csrf_token

    # Prepare headers
    headers = {
        'Cookie': cookies,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Referer': 'https://hr.talenta.co/live-attendance',
        'Origin': 'https://hr.talenta.co',
        'X-Requested-With': 'XMLHttpRequest',
    }

    if csrf_token:
        headers['X-CSRF-TOKEN'] = csrf_token

    return {
        'url': 'https://hr.talenta.co/api/web/live-attendance/request',
        'data': data,
        'headers': headers,
    }


def attendance_post(lat: str, long: str, cookies: str, desc: str, is_checkout: bool = False) -> Any:
    """
    Post attendance request to Talenta API

    Args:
        lat: Latitude coordinate
        long: Longitude coordinate
        cookies: Session cookie string
        desc: Description message
        is_checkout: True for checkout, False for checkin

    Returns:
        Response data (JSON or text)

    Raises:
        Exception: If request fails
    """
    config = prep_form(lat, long, cookies, desc, is_checkout)

    try:
        response = requests.post(
            config['url'],
            data=config['data'],
            headers=config['headers'],
            timeout=30
        )

        if not response.ok:
            error_text = response.text
            raise Exception(
                f"HTTP {response.status_code}: {response.reason}\n{error_text}"
            )

        # Try to parse as JSON, fallback to text
        try:
            return response.json()
        except ValueError:
            return response.text

    except requests.exceptions.RequestException as error:
        raise Exception(f"Request failed: {error}")


def clock_in(lat: str, long: str, cookies: str, desc: str = "Hello I am In") -> Any:
    """
    Clock in to Talenta

    Args:
        lat: Latitude coordinate
        long: Longitude coordinate
        cookies: Session cookie string
        desc: Check-in description message

    Returns:
        Response data from API
    """
    return attendance_post(lat, long, cookies, desc, is_checkout=False)


def clock_out(lat: str, long: str, cookies: str, desc: str = "Goodbye I am Out") -> Any:
    """
    Clock out from Talenta

    Args:
        lat: Latitude coordinate
        long: Longitude coordinate
        cookies: Session cookie string
        desc: Check-out description message

    Returns:
        Response data from API
    """
    return attendance_post(lat, long, cookies, desc, is_checkout=True)


def fetch_cookies(email: str, password: str) -> str:
    """
    Fetch cookies automatically using username and password

    Args:
        email: User email
        password: User password

    Returns:
        Cookie string for use with clock_in/clock_out

    Raises:
        Exception: If authentication fails
    """
    session = requests.Session()

    try:
        # Step 1: Get login page and extract authenticity token
        logger.info('🔐 Starting authentication process...')

        login_page_url = 'https://account.mekari.com/users/sign_in?app_referer=Talenta'
        login_page_response = session.get(
            login_page_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            },
            timeout=30
        )

        if not login_page_response.ok:
            raise Exception(f"Failed to load login page: {login_page_response.status_code}")

        login_page_html = login_page_response.text
        authenticity_token = extract_authenticity_token(login_page_html)

        if not authenticity_token:
            raise Exception('Could not extract authenticity token from login page')

        logger.info('✅ Successfully extracted authenticity token')

        # Step 2: Submit login form
        logger.info('🔑 Submitting login credentials...')

        login_data = {
            'utf8': '✓',
            'authenticity_token': authenticity_token,
            'user[email]': email,
            'no-captcha-token': '',
            'user[password]': password,
        }

        login_response = session.post(
            login_page_url,
            data=login_data,
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Referer': login_page_url,
                'Origin': 'https://account.mekari.com',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            },
            allow_redirects=False,
            timeout=30
        )

        # Check for successful login (should get 302 redirect)
        if login_response.status_code != 302:
            error_text = login_response.text
            if 'Invalid email or password' in error_text:
                raise Exception('Invalid email or password')
            raise Exception(f"Login failed: {login_response.status_code} {login_response.reason}")

        logger.info('✅ Login successful')

        # Step 3: Get authorization code
        logger.info('🔗 Getting authorization code...')

        auth_url = 'https://account.mekari.com/auth?client_id=TAL-73645&response_type=code&scope=sso:profile'
        auth_response = session.get(
            auth_url,
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Referer': login_page_url,
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            },
            allow_redirects=False,
            timeout=30
        )

        if auth_response.status_code != 302:
            raise Exception(f"Authorization failed: {auth_response.status_code} {auth_response.reason}")

        location_header = auth_response.headers.get('location')
        if not location_header or 'hr.talenta.co/sso-callback' not in location_header:
            raise Exception('Invalid authorization redirect')

        logger.info('✅ Authorization successful')

        # Step 4: Follow redirect to get final cookies
        logger.info('🍪 Getting final session cookies...')

        final_response = session.get(
            location_header,
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            },
            allow_redirects=False,
            timeout=30
        )

        # Extract cookies from session
        cookies_dict = session.cookies.get_dict()

        if not cookies_dict:
            raise Exception('Failed to get session cookies from Talenta')

        logger.info('✅ Successfully obtained session cookies')

        # Extract PHPSESSID or _identity cookie specifically
        if 'PHPSESSID' in cookies_dict:
            return f"PHPSESSID={cookies_dict['PHPSESSID']}"
        elif '_identity' in cookies_dict:
            return f"_identity={cookies_dict['_identity']}"

        # If no specific cookie found, return all cookies
        cookie_string = '; '.join([f"{k}={v}" for k, v in cookies_dict.items()])
        return cookie_string

    except Exception as error:
        logger.error(f'❌ Cookie fetching failed: {error}')
        raise


def _calculate_api_start_date(target_date: datetime) -> str:
    """
    Calculate the start_date parameter for the attendance API.

    The API returns periods based on the MONTH of the start_date:
    - start_date in January → returns Dec 21 - Jan 20
    - start_date in February → returns Jan 21 - Feb 20

    Talenta attendance periods use cutoff date of 20th:
    - Period Dec 21 - Jan 20: target dates Dec 21 to Jan 20 → use start_date in Jan
    - Period Jan 21 - Feb 20: target dates Jan 21 to Feb 20 → use start_date in Feb

    Args:
        target_date: The date we want to look up in the schedule.

    Returns:
        Start date string in YYYY-MM-DD format that will fetch the correct period.
    """
    day = target_date.day
    month = target_date.month
    year = target_date.year

    # If day is 21-31, target is in period that ends on 20th of NEXT month
    # So we need start_date in NEXT month
    if day >= 21:
        # Move to next month
        if month == 12:
            api_month = 1
            api_year = year + 1
        else:
            api_month = month + 1
            api_year = year
    else:
        # Day 1-20: target is in period ending on 20th of CURRENT month
        # So start_date should be in current month
        api_month = month
        api_year = year

    return f"{api_year}-{api_month:02d}-01"


def get_schedule(start_date: Optional[str] = None, cookies: Optional[str] = None, target_date: Optional[datetime] = None) -> Optional[Dict]:
    """
    Fetch attendance schedule from Talenta.

    Tries methods in order:
    1. Automatic Bearer token extraction from session (recommended)
    2. Manual Bearer token from config (fallback if auto extraction fails)

    Args:
        start_date: Start date in YYYY-MM-DD format. If None, calculated from target_date.
        cookies: Session cookies for authentication (not used, here for API compatibility).
        target_date: Optional datetime for calculating which attendance period to fetch.
                    Important for dates near the 20th/21st boundary.

    Returns:
        Dict with schedule data or None if request fails.
    """
    if not MEKARI_ORGANISATION_ID or not MEKARI_ORGANISATION_USER_ID:
        logger.warning("Schedule check not configured. Set MEKARI_ORGANISATION_ID and MEKARI_ORGANISATION_USER_ID.")
        return None

    # Calculate start_date based on target_date if not specified
    if not start_date:
        try:
            tz = ZoneInfo(TIMEZONE)
            if target_date:
                start_date = _calculate_api_start_date(target_date)
            else:
                start_date = _calculate_api_start_date(datetime.now(tz))
        except:
            from datetime import timezone, timedelta
            tz = timezone(timedelta(hours=7))
            if target_date:
                start_date = _calculate_api_start_date(target_date)
            else:
                start_date = _calculate_api_start_date(datetime.now(tz))

    # Method 1: Try automatic Bearer token extraction from session
    bearer_token = _get_bearer_token_from_session()
    if bearer_token:
        result = _get_schedule_with_bearer(start_date, bearer_token)
        if result:
            return result

    # Method 2: Fallback to manual Bearer token from config
    if MEKARI_BEARER_TOKEN:
        result = _get_schedule_with_bearer(start_date, MEKARI_BEARER_TOKEN)
        if result:
            return result

    logger.warning("Could not fetch schedule. Check EMAIL/PASSWORD credentials.")
    return None


def _extract_bearer_token_from_session(session_token: str) -> Optional[str]:
    """
    Extract Bearer token from the _session_token cookie value.

    The cookie is URL-encoded PHP serialized data containing a UUID-style token.
    Format: hash:2:{i:0;s:14:"_session_token";i:1;s:69:"uuid_token";}

    Args:
        session_token: The raw _session_token cookie value.

    Returns:
        The Bearer token string or None if extraction fails.
    """
    import urllib.parse

    try:
        # URL decode the cookie value
        decoded = urllib.parse.unquote(session_token)

        # Split by quotes to extract the token
        parts = decoded.split('"')

        # Find the UUID token (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx_something)
        for part in parts:
            if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}_', part):
                return part

        return None
    except Exception:
        return None


def _get_bearer_token_from_session(cookies: Optional[str] = None) -> Optional[str]:
    """
    Get Bearer token for Mekari API by logging in and extracting from session.

    This performs a full login flow and extracts the Bearer token from
    the _session_token cookie that Talenta sets.

    Args:
        cookies: Optional existing cookies string (not used, here for API compatibility).

    Returns:
        Bearer token string or None if extraction fails.
    """
    try:
        from src.config.config_local import EMAIL, PASSWORD

        if not EMAIL or not PASSWORD:
            return None

        session = requests.Session()

        # Step 1: Get login page and extract authenticity token
        login_url = 'https://account.mekari.com/users/sign_in?app_referer=Talenta'
        response = session.get(login_url, timeout=30)

        match = re.search(r'name="authenticity_token" value="([^"]+)"', response.text)
        if not match:
            logger.debug("Could not extract authenticity token for Bearer token extraction")
            return None

        auth_token = match.group(1)

        # Step 2: Submit login
        login_data = {
            'utf8': '✓',
            'authenticity_token': auth_token,
            'user[email]': EMAIL,
            'no-captcha-token': '',
            'user[password]': PASSWORD,
        }

        response = session.post(login_url, data=login_data, allow_redirects=False, timeout=30)

        if response.status_code != 302:
            logger.debug("Login failed during Bearer token extraction")
            return None

        # Step 3: Follow OAuth flow
        auth_url = 'https://account.mekari.com/auth?client_id=TAL-73645&response_type=code&scope=sso:profile'
        response = session.get(auth_url, allow_redirects=False, timeout=30)

        redirect_url = response.headers.get('location', '')
        if not redirect_url:
            logger.debug("No redirect URL during Bearer token extraction")
            return None

        # Step 4: Follow redirect to Talenta to get session token
        session.get(redirect_url, timeout=30)

        # Step 5: Extract Bearer token from _session_token cookie
        session_token = session.cookies.get('_session_token', '')
        if not session_token:
            logger.debug("No _session_token cookie found")
            return None

        bearer_token = _extract_bearer_token_from_session(session_token)
        if bearer_token:
            logger.debug("Successfully extracted Bearer token from session")
            return bearer_token

        return None

    except Exception as error:
        logger.debug(f"Error getting Bearer token from session: {error}")
        return None


def _get_schedule_with_bearer(start_date: str, bearer_token: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch schedule using Bearer token authentication via api.mekari.com.

    Args:
        start_date: Start date in YYYY-MM-DD format.
        bearer_token: Optional Bearer token. If None, uses MEKARI_BEARER_TOKEN from config.

    Returns:
        Dict with schedule data or None if request fails.
    """
    token = bearer_token or MEKARI_BEARER_TOKEN
    if not token or not MEKARI_ORGANISATION_ID or not MEKARI_ORGANISATION_USER_ID:
        return None

    try:
        url = (
            f"https://api.mekari.com/internal/talenta-attendance-web/v2/"
            f"organisations/{MEKARI_ORGANISATION_ID}/summary_attendance_clocks"
        )

        params = {
            'source': 'web',
            'organisation_user_id': MEKARI_ORGANISATION_USER_ID,
            'start_date': start_date,
            'order': 'asc',
            'sort': 'schedule_date',
            'page': '1',
            'limit': '1000000'
        }

        headers = {
            'Accept': '*/*',
            'Authorization': f'Bearer {token}',
            'Origin': 'https://hr.talenta.co',
            'Referer': 'https://hr.talenta.co/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }

        response = requests.get(url, params=params, headers=headers, timeout=30)

        if response.ok:
            logger.info("📅 Fetched schedule using Bearer token")
            return response.json()
        else:
            logger.debug(f"Bearer token schedule fetch failed: HTTP {response.status_code}")
            return None

    except Exception as error:
        logger.debug(f"Bearer token schedule fetch error: {error}")
        return None


def get_shift_for_date(target_date: str) -> Optional[Dict]:
    """
    Get shift information for a specific date.

    Args:
        target_date: Date in YYYY-MM-DD format.

    Returns:
        Dict with shift info containing:
        - office_hour_name: Shift type (WFA, WFO, dayoff, National Holiday, etc.)
        - holiday: Boolean indicating if it's a holiday
        - work_start: Work start time
        - work_end: Work end time
        - schedule_date: The date
        Returns None if not found or error.
    """
    # Parse target date string to datetime for correct month calculation
    try:
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        logger.error(f"Invalid date format: {target_date}")
        return None

    schedule_data = get_schedule(target_date=target_dt)

    if not schedule_data or 'data' not in schedule_data:
        return None

    for entry in schedule_data['data']:
        attrs = entry.get('attributes', {})
        if attrs.get('schedule_date') == target_date:
            return {
                'office_hour_name': attrs.get('office_hour_name'),
                'holiday': attrs.get('holiday', False),
                'work_start': attrs.get('work_start'),
                'work_end': attrs.get('work_end'),
                'schedule_date': attrs.get('schedule_date'),
                'scheduled_work_total_minute': attrs.get('scheduled_work_total_minute', 0)
            }

    return None


def get_shifts_for_date_range(start_date: str, end_date: str) -> List[Dict]:
    """
    Get shift information for a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format (inclusive).
        end_date: End date in YYYY-MM-DD format (inclusive).

    Returns:
        List of dicts, each containing:
        - date: The date (YYYY-MM-DD)
        - shift: Shift type (WFA, WFO, dayoff, National Holiday, etc.)
        - is_work_day: Boolean indicating if it's a work day
        - holiday: Boolean indicating if it's a holiday

        Returns empty list if date parsing fails or no data found.
    """
    from datetime import timedelta

    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return []

    if start_dt > end_dt:
        logger.error("start_date must be before or equal to end_date")
        return []

    results = []
    current_dt = start_dt

    # Cache schedule data to avoid redundant API calls
    # Key: API start_date (YYYY-MM-01), Value: schedule data
    schedule_cache = {}

    while current_dt <= end_dt:
        date_str = current_dt.strftime('%Y-%m-%d')

        # Calculate which API period this date belongs to
        api_start_date = _calculate_api_start_date(current_dt)

        # Fetch schedule for this period if not cached
        if api_start_date not in schedule_cache:
            schedule_data = get_schedule(start_date=api_start_date, target_date=current_dt)
            schedule_cache[api_start_date] = schedule_data

        # Look up this date in the cached schedule
        shift_info = None
        schedule_data = schedule_cache.get(api_start_date)

        if schedule_data and 'data' in schedule_data:
            for entry in schedule_data['data']:
                attrs = entry.get('attributes', {})
                if attrs.get('schedule_date') == date_str:
                    shift_info = attrs
                    break

        if shift_info:
            office_hour = shift_info.get('office_hour_name', '')
            is_holiday = shift_info.get('holiday', False)
            is_work = office_hour.lower() in ['wfa', 'wfo'] and not is_holiday

            results.append({
                'date': date_str,
                'shift': office_hour,
                'is_work_day': is_work,
                'holiday': is_holiday
            })
        else:
            # Date not found in schedule
            results.append({
                'date': date_str,
                'shift': None,
                'is_work_day': None,
                'holiday': None
            })

        current_dt += timedelta(days=1)

    return results


def get_tomorrow_shift() -> Optional[Dict]:
    """
    Get shift information for tomorrow.

    Returns:
        Dict with shift info or None if not found.
    """
    try:
        tz = ZoneInfo(TIMEZONE)
        today = datetime.now(tz)
        from datetime import timedelta
        tomorrow = today + timedelta(days=1)
        tomorrow_str = tomorrow.strftime('%Y-%m-%d')

        return get_shift_for_date(tomorrow_str)
    except Exception as error:
        logger.error(f"Error getting tomorrow's shift: {error}")
        return None


def get_today_shift() -> Optional[Dict]:
    """
    Get shift information for today.

    Returns:
        Dict with shift info or None if not found.
    """
    try:
        tz = ZoneInfo(TIMEZONE)
        today = datetime.now(tz)
        today_str = today.strftime('%Y-%m-%d')

        return get_shift_for_date(today_str)
    except Exception as error:
        logger.error(f"Error getting today's shift: {error}")
        return None


def is_work_day(shift_info: Optional[Dict] = None) -> bool:
    """
    Check if today is a work day based on shift info.

    Args:
        shift_info: Optional shift info dict. If None, fetches today's shift.

    Returns:
        True if it's a work day (WFA or WFO), False otherwise.
    """
    if shift_info is None:
        shift_info = get_today_shift()

    if not shift_info:
        # If we can't determine, default to checking weekday
        logger.warning("Could not fetch shift info, falling back to weekday check")
        try:
            tz = ZoneInfo(TIMEZONE)
            today = datetime.now(tz)
            return today.weekday() < 5  # Monday=0, Friday=4
        except:
            return True

    office_hour = shift_info.get('office_hour_name', '').lower()
    is_holiday = shift_info.get('holiday', False)

    # Not a work day if holiday flag is set or office_hour is not WFA/WFO
    if is_holiday:
        return False

    # Work days are WFA and WFO
    return office_hour in ['wfa', 'wfo']


if __name__ == '__main__':
    # Example usage
    logger.info("Talenta API Module - Python Implementation")
    logger.info("Import this module to use clock_in(), clock_out(), and fetch_cookies()")
