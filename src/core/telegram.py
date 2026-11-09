"""
Telegram notification module for Talenta Flask application
"""

import requests
from src.core.logger import get_logger
from src.config import config_local

# Initialize logger
logger = get_logger('talenta_scheduler')


def send_telegram_message(message: str, account: dict = None) -> bool:
    """
    Send a message via Telegram Bot API.

    Args:
        message (str): The message text to send.
        account (dict): Optional account dict. If it carries its own Telegram
            bot token/chat id, those are used; otherwise the global config values
            act as a fallback so a shared bot can serve every account.

    Returns:
        bool: True if the message was sent successfully, False otherwise.
    """

    telegram_bot_token = ''
    telegram_chat_id = ''
    if account:
        telegram_bot_token = account.get('telegram_bot_token') or ''
        telegram_chat_id = account.get('telegram_chat_id') or ''

    telegram_bot_token = telegram_bot_token or config_local.TELEGRAM_BOT_TOKEN
    telegram_chat_id = telegram_chat_id or config_local.TELEGRAM_CHAT_ID

    if not telegram_bot_token or not telegram_chat_id:
        logger.debug("Telegram not configured; skipping notification.")
        return False

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