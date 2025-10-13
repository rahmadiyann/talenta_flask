"""
Authentication helper functions for Talenta API
"""

import re
from typing import Optional, Dict


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
