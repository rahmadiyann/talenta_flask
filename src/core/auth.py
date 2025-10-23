"""
Authentication helper functions for Talenta API
"""

import re
from typing import Optional, Dict


def get_cookies():
    """
    Get authentication cookies (automatic or manual)

    Returns:
        Cookie string

    Raises:
        Exception: If authentication fails
    """
    # Import here to avoid circular dependency
    from src.api import talenta
    from src.config import config_local
    from src.core.logger import get_logger

    logger = get_logger('talenta_auth')

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


def extract_authenticity_token(html: str) -> Optional[str]:
    """
    Extract authenticity token from login page HTML

    Args:
        html: HTML content of the login page

    Returns:
        The authenticity token or None if not found
    """
    token_patterns = [
        r'name="authenticity_token" value="([^"]+)"',
        r'<input[^>]*name="authenticity_token"[^>]*value="([^"]+)"',
        r'authenticity_token[^"]*"([^"]+)"',
    ]

    for pattern in token_patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)

    return None


def extract_cookies(headers: Dict[str, str]) -> str:
    """
    Extract cookies from response headers

    Args:
        headers: Response headers dictionary

    Returns:
        Formatted cookie string
    """
    set_cookie = headers.get('set-cookie', '')

    if not set_cookie:
        return ''

    # Split by comma and extract cookie name=value pairs
    cookies = []
    for cookie in set_cookie.split(','):
        cookie_part = cookie.strip().split(';')[0]
        if cookie_part:
            cookies.append(cookie_part)

    return '; '.join(cookies)
