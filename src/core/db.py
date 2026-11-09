"""
SQLite persistence layer for the Talenta admin panel.

Stores multiple Talenta accounts and a rolling action log. The database is a
single file (default: ``data/talenta.db``) shared between the scheduler process
and the Flask/Gunicorn web process, so all cross-process state lives here rather
than in memory.
"""

import os
import sqlite3
import threading
from contextlib import contextmanager

from src.core.logger import get_logger

logger = get_logger('talenta_db')

# Project root: .../talenta_flask
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Default DB path can be overridden with DB_PATH (useful for mounting a volume).
DB_PATH = os.getenv('DB_PATH', os.path.join(_BASE_DIR, 'data', 'talenta.db'))

# Serialize schema init; SQLite itself handles concurrent access across processes
# via file locking, but we guard our own one-time init within a process.
_init_lock = threading.Lock()
_initialized = False


def _ensure_dir() -> None:
    """Create the directory that will hold the SQLite file if it is missing."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)


@contextmanager
def get_connection():
    """
    Yield a SQLite connection with Row factory and foreign keys enabled.

    Commits on success, rolls back on exception, and always closes.
    """
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Columns that make up an account, used by the accounts module for safe inserts.
ACCOUNT_COLUMNS = [
    'label', 'email', 'password', 'cookies',
    'latitude', 'longitude',
    'clock_in_time', 'clock_out_time', 'jitter_minutes',
    'wfa_only', 'enabled',
    'mekari_org_id', 'mekari_org_user_id', 'bearer_token',
    'telegram_bot_token', 'telegram_chat_id',
]


def init_db() -> None:
    """Create tables if they do not exist. Safe to call repeatedly."""
    global _initialized
    if _initialized:
        return

    with _init_lock:
        if _initialized:
            return

        with get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    label               TEXT    NOT NULL,
                    email               TEXT    NOT NULL DEFAULT '',
                    password            TEXT    NOT NULL DEFAULT '',
                    cookies             TEXT    NOT NULL DEFAULT '',
                    latitude            TEXT    NOT NULL DEFAULT '-6.000',
                    longitude           TEXT    NOT NULL DEFAULT '107.000',
                    clock_in_time       TEXT    NOT NULL DEFAULT '08:50',
                    clock_out_time      TEXT    NOT NULL DEFAULT '18:15',
                    jitter_minutes      INTEGER NOT NULL DEFAULT 10,
                    wfa_only            INTEGER NOT NULL DEFAULT 1,
                    enabled             INTEGER NOT NULL DEFAULT 1,
                    mekari_org_id       TEXT    NOT NULL DEFAULT '',
                    mekari_org_user_id  TEXT    NOT NULL DEFAULT '',
                    bearer_token        TEXT    NOT NULL DEFAULT '',
                    telegram_bot_token  TEXT    NOT NULL DEFAULT '',
                    telegram_chat_id    TEXT    NOT NULL DEFAULT '',
                    created_at          TEXT    NOT NULL DEFAULT '',
                    updated_at          TEXT    NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS action_log (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id    INTEGER,
                    account_label TEXT    NOT NULL DEFAULT '',
                    action        TEXT    NOT NULL DEFAULT '',
                    status        TEXT    NOT NULL DEFAULT '',
                    message       TEXT    NOT NULL DEFAULT '',
                    trigger       TEXT    NOT NULL DEFAULT 'auto',
                    created_at    TEXT    NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_action_log_created
                    ON action_log (created_at DESC);
                """
            )

        logger.info(f'🗄️  Database ready at {DB_PATH}')
        _initialized = True
