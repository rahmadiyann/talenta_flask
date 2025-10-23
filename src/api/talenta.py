"""
Talenta API Module - Python Implementation
Main module for clocking in and out of Mekari Talenta HR system
"""

import base64
import codecs
import re
import requests
from datetime import datetime
from typing import Dict, Optional, Any
from src.core.auth import extract_authenticity_token, extract_cookies
from src.core.logger import setup_logger
from src.config.config_local import TIMEZONE

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
        # Get today's date in the configured timezone
        try:
            tz = ZoneInfo(TIMEZONE)
            today = datetime.now(tz).strftime('%Y-%m-%d')
        except Exception as tz_error:
            logger.warning(f"⚠️  Timezone error, using system time: {tz_error}")
            today = datetime.now().strftime('%Y-%m-%d')

        headers = {
            'Cookie': cookies,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }

        # PRIMARY APPROACH: Try API endpoint first
        try:
            logger.info('🔍 Checking attendance status via API endpoint...')
            api_response = requests.get(
                'https://hr.talenta.co/api/web/live-attendance',
                headers=headers,
                timeout=10
            )

            if api_response.status_code == 200:
                try:
                    data = api_response.json()

                    # Handle different response formats
                    records = []
                    if isinstance(data, list):
                        records = data
                    elif isinstance(data, dict) and 'data' in data:
                        records = data['data'] if isinstance(data['data'], list) else []

                    # Filter for today's attendance record
                    today_record = None
                    for record in records:
                        # Check both 'date' and 'clock_date' fields (different API variants)
                        record_date = record.get('date') or record.get('clock_date')
                        if record_date and record_date.startswith(today):
                            today_record = record
                            break

                    if today_record:
                        # Check clock in/out status
                        has_clocked_in = bool(
                            today_record.get('final_check_in') or
                            today_record.get('clock_time')
                        )
                        has_clocked_out = bool(today_record.get('final_check_out'))

                        logger.info(f'✅ Attendance status retrieved: clocked_in={has_clocked_in}, clocked_out={has_clocked_out}')
                        return {
                            'has_clocked_in': has_clocked_in,
                            'has_clocked_out': has_clocked_out
                        }
                    else:
                        # No record for today - user hasn't clocked in yet
                        logger.info('✅ No attendance record found for today')
                        return default_status

                except (ValueError, KeyError) as parse_error:
                    logger.warning(f'⚠️  Failed to parse API response: {parse_error}')
                    # Fall through to HTML parsing
            else:
                logger.warning(f'⚠️  API endpoint returned status {api_response.status_code}')
                # Fall through to HTML parsing

        except requests.exceptions.RequestException as api_error:
            logger.warning(f'⚠️  API request failed: {api_error}')
            # Fall through to HTML parsing

        # FALLBACK APPROACH: Parse HTML page
        logger.info('🔍 Falling back to HTML parsing...')

        try:
            html_response = requests.get(
                'https://hr.talenta.co/live-attendance',
                headers=headers,
                timeout=10
            )

            if html_response.status_code == 200:
                html = html_response.text

                # Look for attendance status indicators in HTML
                # Pattern 1: Look for "Clock In" button (indicates not clocked in)
                clock_in_button = re.search(r'Clock\s+In', html, re.IGNORECASE)

                # Pattern 2: Look for "Clock Out" button (indicates clocked in but not out)
                clock_out_button = re.search(r'Clock\s+Out', html, re.IGNORECASE)

                # Pattern 3: Look for time stamps or status indicators
                # Format: "HH:MM" or "HH:MM:SS"
                time_pattern = r'(\d{2}:\d{2}(?::\d{2})?)'
                time_matches = re.findall(time_pattern, html)

                # Logic:
                # - If "Clock In" button is present, user hasn't clocked in
                # - If "Clock Out" button is present, user has clocked in but not out
                # - If neither button is present and time stamps exist, user may have clocked out

                has_clocked_in = False
                has_clocked_out = False

                if not clock_in_button and (clock_out_button or time_matches):
                    # No "Clock In" button but "Clock Out" button or timestamps present
                    has_clocked_in = True

                    # Check if already clocked out (no "Clock Out" button)
                    if not clock_out_button and len(time_matches) >= 2:
                        # Multiple timestamps suggest both clock in and out
                        has_clocked_out = True

                logger.info(f'✅ Attendance status from HTML: clocked_in={has_clocked_in}, clocked_out={has_clocked_out}')
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


if __name__ == '__main__':
    # Example usage
    logger.info("Talenta API Module - Python Implementation")
    logger.info("Import this module to use clock_in(), clock_out(), and fetch_cookies()")
