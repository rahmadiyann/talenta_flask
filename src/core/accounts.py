"""
Account management for the Talenta admin panel.

Each account is an independent Talenta/Mekari identity with its own credentials,
location, clock in/out schedule and notification settings. The scheduler and the
web API both operate on these records.
"""

from datetime import datetime
from typing import Dict, List, Optional

from src.core import db
from src.core.logger import get_logger

logger = get_logger('talenta_accounts')

# Fields the caller is allowed to set when creating/updating an account.
# ``id``, ``created_at`` and ``updated_at`` are managed internally.
_WRITABLE = set(db.ACCOUNT_COLUMNS)

# Fields stored as 0/1 in SQLite but exposed as real booleans in Python/JSON.
_BOOL_FIELDS = {'wfa_only', 'enabled'}

# Fields that hold secrets — stripped from "public" representations sent to the UI.
_SECRET_FIELDS = {'password', 'cookies', 'bearer_token', 'telegram_bot_token'}


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')


def _row_to_account(row) -> Dict:
    """Convert a sqlite3.Row into a typed account dict."""
    account = dict(row)
    for field in _BOOL_FIELDS:
        account[field] = bool(account.get(field, 0))
    return account


def _coerce_writable(data: Dict) -> Dict:
    """Keep only writable keys and normalize booleans to 0/1 for storage."""
    clean = {}
    for key, value in data.items():
        if key not in _WRITABLE:
            continue
        if key in _BOOL_FIELDS:
            clean[key] = 1 if value in (True, 1, '1', 'true', 'True', 'on') else 0
        elif key == 'jitter_minutes':
            try:
                clean[key] = max(0, int(value))
            except (TypeError, ValueError):
                clean[key] = 0
        else:
            clean[key] = '' if value is None else str(value)
    return clean


def public_account(account: Dict) -> Dict:
    """
    Return a copy safe to send to the browser: secrets are replaced with
    ``has_<field>`` booleans so the UI can show whether a value is set without
    ever leaking it.
    """
    safe = {k: v for k, v in account.items() if k not in _SECRET_FIELDS}
    for field in _SECRET_FIELDS:
        safe[f'has_{field}'] = bool(account.get(field))
    return safe


def list_accounts() -> List[Dict]:
    db.init_db()
    with db.get_connection() as conn:
        rows = conn.execute('SELECT * FROM accounts ORDER BY id ASC').fetchall()
    return [_row_to_account(row) for row in rows]


def get_account(account_id: int) -> Optional[Dict]:
    db.init_db()
    with db.get_connection() as conn:
        row = conn.execute(
            'SELECT * FROM accounts WHERE id = ?', (account_id,)
        ).fetchone()
    return _row_to_account(row) if row else None


def create_account(data: Dict) -> Dict:
    db.init_db()
    fields = _coerce_writable(data)

    if not fields.get('label'):
        raise ValueError('Account label is required')
    if not fields.get('email') and not fields.get('cookies'):
        raise ValueError('Provide either email/password or a manual cookie')

    now = _now()
    columns = list(fields.keys()) + ['created_at', 'updated_at']
    placeholders = ', '.join(['?'] * len(columns))
    values = list(fields.values()) + [now, now]

    with db.get_connection() as conn:
        cursor = conn.execute(
            f'INSERT INTO accounts ({", ".join(columns)}) VALUES ({placeholders})',
            values,
        )
        account_id = cursor.lastrowid

    logger.info(f"➕ Created account #{account_id} ({fields.get('label')})")
    return get_account(account_id)


def update_account(account_id: int, data: Dict) -> Optional[Dict]:
    db.init_db()
    existing = get_account(account_id)
    if not existing:
        return None

    fields = _coerce_writable(data)

    # Treat blank secret fields as "leave unchanged" so the UI can omit them
    # when editing without wiping stored credentials.
    for field in _SECRET_FIELDS:
        if field in fields and fields[field] == '':
            del fields[field]

    if not fields:
        return existing

    fields['updated_at'] = _now()
    assignments = ', '.join([f'{key} = ?' for key in fields])
    values = list(fields.values()) + [account_id]

    with db.get_connection() as conn:
        conn.execute(
            f'UPDATE accounts SET {assignments} WHERE id = ?', values
        )

    logger.info(f'✏️  Updated account #{account_id}')
    return get_account(account_id)


def set_enabled(account_id: int, enabled: bool) -> Optional[Dict]:
    return update_account(account_id, {'enabled': enabled})


def delete_account(account_id: int) -> bool:
    db.init_db()
    with db.get_connection() as conn:
        cursor = conn.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
        deleted = cursor.rowcount > 0
    if deleted:
        logger.info(f'🗑️  Deleted account #{account_id}')
    return deleted


def log_action(account: Optional[Dict], action: str, status: str,
               message: str = '', trigger: str = 'auto') -> None:
    """Record a clock in/out attempt so the panel can show recent activity."""
    try:
        db.init_db()
        with db.get_connection() as conn:
            conn.execute(
                '''INSERT INTO action_log
                   (account_id, account_label, action, status, message, trigger, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (
                    account.get('id') if account else None,
                    account.get('label', '') if account else '',
                    action, status, message, trigger, _now(),
                ),
            )
    except Exception as error:  # logging must never break a clock action
        logger.warning(f'Failed to write action log: {error}')


def recent_logs(limit: int = 50) -> List[Dict]:
    db.init_db()
    with db.get_connection() as conn:
        rows = conn.execute(
            'SELECT * FROM action_log ORDER BY id DESC LIMIT ?', (int(limit),)
        ).fetchall()
    return [dict(row) for row in rows]


def seed_from_env() -> None:
    """
    On first run, migrate the single account configured via environment
    variables / config_local into the database so existing setups keep working.
    """
    db.init_db()
    if list_accounts():
        return

    try:
        from src.config import config_local as cfg
    except Exception as error:
        logger.debug(f'No config_local to seed from: {error}')
        return

    email = getattr(cfg, 'EMAIL', '') or ''
    cookies = getattr(cfg, 'COOKIES_TALENTA', '') or ''
    if cookies == 'PHPSESSID=<value>':
        cookies = ''

    if not email and not cookies:
        logger.info('No .env account to seed; start by adding one in the panel.')
        return

    create_account({
        'label': email.split('@')[0] if email else 'Default',
        'email': email,
        'password': getattr(cfg, 'PASSWORD', '') or '',
        'cookies': cookies,
        'latitude': getattr(cfg, 'LATITUDE', '-6.000') or '-6.000',
        'longitude': getattr(cfg, 'LONGITUDE', '107.000') or '107.000',
        'clock_in_time': getattr(cfg, 'TIME_CLOCK_IN', '08:50') or '08:50',
        'clock_out_time': getattr(cfg, 'TIME_CLOCK_OUT', '18:15') or '18:15',
        'wfa_only': True,
        'enabled': True,
        'mekari_org_id': getattr(cfg, 'MEKARI_ORGANISATION_ID', '') or '',
        'mekari_org_user_id': getattr(cfg, 'MEKARI_ORGANISATION_USER_ID', '') or '',
        'bearer_token': getattr(cfg, 'MEKARI_BEARER_TOKEN', '') or '',
        'telegram_bot_token': getattr(cfg, 'TELEGRAM_BOT_TOKEN', '') or '',
        'telegram_chat_id': getattr(cfg, 'TELEGRAM_CHAT_ID', '') or '',
    })
    logger.info('🌱 Seeded initial account from environment configuration')
