"""
Configuration file for Talenta API
Loads configuration from environment variables (.env file)
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Authentication Methods:
# Method 1 (Recommended): Use email and password for automatic authentication
# Method 2 (Fallback): Use manual cookies from browser

# Method 1: Automatic authentication (recommended)
EMAIL = os.getenv('EMAIL', '')  # Your Talenta/Mekari email address
PASSWORD = os.getenv('PASSWORD', '')  # Your Talenta/Mekari password

# Method 2: Manual cookie authentication (fallback)
# You can use the `_identity=` or `PHPSESSID=` cookie
cookies_value = os.getenv('COOKIES_TALENTA', '')
if cookies_value and not cookies_value.startswith('PHPSESSID=') and not cookies_value.startswith('_identity='):
    COOKIES_TALENTA = f'PHPSESSID={cookies_value}'
else:
    COOKIES_TALENTA = cookies_value

# Location settings (fallback if auto-detection fails)
LONGITUDE = os.getenv('LONGITUDE', '107.000')
LATITUDE = os.getenv('LATITUDE', '-6.000')

# Schedule settings (for scheduler.py)
TIME_CLOCK_IN = os.getenv('TIME_CLOCK_IN', '09:00')
TIME_CLOCK_OUT = os.getenv('TIME_CLOCK_OUT', '17:00')

# Timezone setting
TIMEZONE = os.getenv('TZ', 'Asia/Jakarta')
