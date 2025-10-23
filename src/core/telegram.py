"""
Telegram notification module for Talenta Flask application
"""

import requests
from src.config.config_local import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.core.logger import get_logger

# Initialize logger
logger = get_logger('talenta_scheduler')


def send_telegram_message(message: str) -> bool:
    """
    Send a message via Telegram Bot API.

    Args:
        message (str): The message text to send.

    Returns:
        bool: True if the message was sent successfully, False otherwise.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram is not configured. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Telegram message sent successfully.")
            return True
        else:
            logger.error(f"Failed to send Telegram message. Status code: {response.status_code}, Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while sending Telegram message: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while sending Telegram message: {e}")
        return False