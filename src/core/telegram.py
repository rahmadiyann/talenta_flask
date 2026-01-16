"""
Telegram notification module for Talenta Flask application
"""

import requests
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

    telegram_bot_token = "8578824358:AAEBW3s3wbkn3VpbozCd91VsDCBw2JF1o8I"
    telegram_chat_id = "8193662464"

    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": telegram_chat_id,
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