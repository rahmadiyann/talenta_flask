"""
Flask server for the Talenta multi-account admin panel.

Serves a password-protected admin UI and a JSON REST API to manage Talenta
accounts, trigger manual clock in/out, toggle automation, and view each
account's shift schedule. State is persisted in SQLite (see ``src.core.db``),
so this process and the background scheduler stay in sync.

Public endpoints:
    GET  /login          - login page
    POST /login          - authenticate (sets session)
    GET  /logout         - clear session
    GET  /health         - health check (unauthenticated)

Authenticated page:
    GET  /               - admin panel SPA

Authenticated JSON API (all under /api):
    GET    /api/accounts
    POST   /api/accounts
    GET    /api/accounts/<id>
    PUT    /api/accounts/<id>
    DELETE /api/accounts/<id>
    POST   /api/accounts/<id>/clockin
    POST   /api/accounts/<id>/clockout
    POST   /api/accounts/<id>/enabled      body: {"enabled": bool}
    GET    /api/accounts/<id>/today
    GET    /api/accounts/<id>/schedule?start_date=&end_date=
    GET    /api/logs?limit=
"""

import hmac
import os
from functools import wraps

from flask import Flask, request, jsonify, session, redirect, url_for

from src.core.logger import get_logger
from src.core import accounts
from src.api import admin_ui

app = Flask(__name__)
app.logger.disabled = True
app.config['JSON_SORT_KEYS'] = False

# Session signing key. Set SECRET_KEY in the environment for stable sessions
# across restarts; a random fallback is generated otherwise (logs out users on
# restart but keeps things secure).
app.secret_key = os.getenv('SECRET_KEY') or os.urandom(32)

logger = get_logger('talenta_server')

# Admin password for the panel. Strongly recommend setting ADMIN_PASSWORD.
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = 'admin'
    logger.warning('⚠️  ADMIN_PASSWORD not set — using default "admin". Set it in your environment!')

# Prepare the database and migrate any .env-configured account on startup.
try:
    accounts.seed_from_env()
except Exception as _seed_error:  # pragma: no cover
    logger.warning(f'Account seed skipped: {_seed_error}')


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def _is_authed() -> bool:
    return session.get('authed') is True


def login_required(fn):
    """Protect a page route — redirect to /login when not authenticated."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _is_authed():
            return redirect(url_for('login_page'))
        return fn(*args, **kwargs)
    return wrapper


def api_login_required(fn):
    """Protect an API route — return 401 JSON when not authenticated."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _is_authed():
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        return fn(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route('/login', methods=['GET'])
def login_page():
    if _is_authed():
        return redirect(url_for('admin_panel'))
    return admin_ui.render_login()


@app.route('/login', methods=['POST'])
def login_submit():
    password = request.form.get('password', '')
    if hmac.compare_digest(password, ADMIN_PASSWORD):
        session['authed'] = True
        session.permanent = True
        logger.info('🔓 Admin logged in')
        return redirect(url_for('admin_panel'))
    logger.warning('🔒 Failed login attempt')
    return admin_ui.render_login('Incorrect password'), 401


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------
@app.route('/', methods=['GET'])
@login_required
def admin_panel():
    return admin_ui.ADMIN_HTML


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200


@app.route('/favicon.ico')
def favicon():
    return '', 204


# ---------------------------------------------------------------------------
# Account API
# ---------------------------------------------------------------------------
@app.route('/api/accounts', methods=['GET'])
@api_login_required
def api_list_accounts():
    data = [accounts.public_account(a) for a in accounts.list_accounts()]
    return jsonify({'success': True, 'accounts': data}), 200


@app.route('/api/accounts', methods=['POST'])
@api_login_required
def api_create_account():
    try:
        account = accounts.create_account(request.get_json(force=True) or {})
        return jsonify({'success': True, 'account': accounts.public_account(account)}), 201
    except ValueError as error:
        return jsonify({'success': False, 'message': str(error)}), 400
    except Exception as error:
        logger.error(f'Create account failed: {error}')
        return jsonify({'success': False, 'message': str(error)}), 500


@app.route('/api/accounts/<int:account_id>', methods=['GET'])
@api_login_required
def api_get_account(account_id):
    account = accounts.get_account(account_id)
    if not account:
        return jsonify({'success': False, 'message': 'Account not found'}), 404
    return jsonify({'success': True, 'account': accounts.public_account(account)}), 200


@app.route('/api/accounts/<int:account_id>', methods=['PUT'])
@api_login_required
def api_update_account(account_id):
    try:
        account = accounts.update_account(account_id, request.get_json(force=True) or {})
        if not account:
            return jsonify({'success': False, 'message': 'Account not found'}), 404
        return jsonify({'success': True, 'account': accounts.public_account(account)}), 200
    except ValueError as error:
        return jsonify({'success': False, 'message': str(error)}), 400
    except Exception as error:
        logger.error(f'Update account failed: {error}')
        return jsonify({'success': False, 'message': str(error)}), 500


@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
@api_login_required
def api_delete_account(account_id):
    if accounts.delete_account(account_id):
        return jsonify({'success': True, 'message': 'Account deleted'}), 200
    return jsonify({'success': False, 'message': 'Account not found'}), 404


@app.route('/api/accounts/<int:account_id>/enabled', methods=['POST'])
@api_login_required
def api_set_enabled(account_id):
    body = request.get_json(force=True) or {}
    enabled = bool(body.get('enabled'))
    account = accounts.set_enabled(account_id, enabled)
    if not account:
        return jsonify({'success': False, 'message': 'Account not found'}), 404
    return jsonify({'success': True, 'account': accounts.public_account(account)}), 200


@app.route('/api/accounts/<int:account_id>/clockin', methods=['POST'])
@api_login_required
def api_clockin(account_id):
    return _manual_clock(account_id, 'clockin')


@app.route('/api/accounts/<int:account_id>/clockout', methods=['POST'])
@api_login_required
def api_clockout(account_id):
    return _manual_clock(account_id, 'clockout')


def _manual_clock(account_id, action):
    account = accounts.get_account(account_id)
    if not account:
        return jsonify({'success': False, 'message': 'Account not found'}), 404

    # Imported lazily so the web process doesn't pull scheduler deps at import.
    from src.core.jobs import clock_in_for_account, clock_out_for_account

    runner = clock_out_for_account if action == 'clockout' else clock_in_for_account
    try:
        result = runner(account, trigger='manual')
        http = 200 if result.get('success') else 502
        return jsonify({'success': result.get('success'),
                        'message': result.get('message'),
                        'data': result}), http
    except Exception as error:
        logger.error(f'Manual {action} failed: {error}')
        return jsonify({'success': False, 'message': str(error)}), 500


@app.route('/api/accounts/<int:account_id>/today', methods=['GET'])
@api_login_required
def api_today(account_id):
    account = accounts.get_account(account_id)
    if not account:
        return jsonify({'success': False, 'message': 'Account not found'}), 404

    from datetime import datetime
    from src.api.talenta import (
        get_shift_for_date, get_attendance_status_api, get_attendance_status,
    )
    from src.core import auth
    from src.config import config_local

    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(config_local.TIMEZONE)
    except Exception:
        from datetime import timedelta, timezone
        tz = timezone(timedelta(hours=7))

    today = datetime.now(tz).strftime('%Y-%m-%d')
    shift = None
    clocked_in = clocked_out = None
    clock_in_at = clock_out_at = None

    # Single schedule lookup gives both the shift and the real clock in/out times.
    try:
        shift_info = get_shift_for_date(today, account=account)
        if shift_info:
            shift = shift_info.get('office_hour_name')
    except Exception as error:
        logger.debug(f'today shift lookup failed: {error}')

    try:
        status = get_attendance_status_api(account=account)
        if status is not None:
            clocked_in = status.get('has_clocked_in')
            clocked_out = status.get('has_clocked_out')
            clock_in_at = status.get('clock_in')
            clock_out_at = status.get('clock_out')
    except Exception as error:
        logger.debug(f'attendance API status failed: {error}')

    # Fall back to HTML scraping only if the API could not tell us.
    if clocked_in is None:
        try:
            cookies = auth.get_cookies_for_account(account)
            status = get_attendance_status(cookies)
            clocked_in = status.get('has_clocked_in')
            clocked_out = status.get('has_clocked_out')
        except Exception as error:
            logger.debug(f'attendance HTML status failed: {error}')

    return jsonify({
        'success': True,
        'date': today,
        'shift': shift,
        'clocked_in': clocked_in,
        'clocked_out': clocked_out,
        'clock_in_at': clock_in_at,
        'clock_out_at': clock_out_at,
    }), 200


@app.route('/api/accounts/<int:account_id>/schedule', methods=['GET'])
@api_login_required
def api_schedule(account_id):
    account = accounts.get_account(account_id)
    if not account:
        return jsonify({'success': False, 'message': 'Account not found'}), 404

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({'success': False, 'message': 'start_date and end_date are required'}), 400

    from src.api.talenta import get_shifts_for_date_range
    try:
        shifts = get_shifts_for_date_range(start_date, end_date, account=account)
        if not shifts:
            return jsonify({'success': False,
                            'message': 'No schedule data. Check Mekari Organisation IDs for this account.'}), 404
        return jsonify({'success': True, 'start_date': start_date,
                        'end_date': end_date, 'schedule': shifts}), 200
    except Exception as error:
        logger.error(f'Schedule fetch failed: {error}')
        return jsonify({'success': False, 'message': str(error)}), 500


@app.route('/api/logs', methods=['GET'])
@api_login_required
def api_logs():
    try:
        limit = min(int(request.args.get('limit', 50)), 200)
    except ValueError:
        limit = 50
    return jsonify({'success': True, 'logs': accounts.recent_logs(limit)}), 200


@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f'Error processing request: {error}', exc_info=True)
    return jsonify({'success': False, 'message': str(error)}), 500


if __name__ == '__main__':
    logger.info('🚀 Starting Talenta admin panel server (dev mode)...')
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
