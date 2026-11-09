"""
HTML templates for the Talenta admin panel.

Kept separate from the Flask routing in ``server.py`` so the (large) markup does
not clutter the API logic. Everything is a self-contained single-page app using
vanilla JS that talks to the ``/api/*`` endpoints.
"""


def render_login(error: str = '') -> str:
    """Render the login page, optionally with an error banner."""
    banner = f'<div class="error">{error}</div>' if error else ''
    return LOGIN_HTML.replace('<!--ERROR-->', banner)


_BASE_CSS = r"""
    @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap');
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
        --deep:#0f0f10; --bg:#141415; --surface:#19191b; --raised:#232325;
        --line: rgba(237,237,237,0.08); --line-2: rgba(237,237,237,0.14);
        --text:#ededed; --text-2:#a1a1a6; --muted:#85858b;
        --accent:#e8a33d; --accent-ink:#1a1206;
        --pos:#4cc38a; --neg:#e5484d;
        --ease: cubic-bezier(0.22, 1, 0.36, 1);
        --mono: 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace;
    }
    body {
        font-family: 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: var(--bg); color: var(--text);
        font-size: 14px; line-height: 20px; -webkit-font-smoothing: antialiased;
        min-height: 100vh;
    }
    .mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }
    .ic { flex-shrink: 0; vertical-align: middle; }

    /* buttons */
    .btn {
        display: inline-flex; align-items: center; justify-content: center; gap: 8px;
        height: 36px; padding: 0 14px; border-radius: 8px;
        background: var(--raised); border: 1px solid var(--line); color: var(--text);
        font: 500 14px/1 'Geist', sans-serif; cursor: pointer;
        transition: background 140ms var(--ease), border-color 140ms var(--ease), color 140ms var(--ease), transform 120ms var(--ease);
    }
    .btn .ic { color: var(--muted); transition: color 140ms var(--ease); }
    .btn:hover { background: #2a2a2d; border-color: var(--line-2); }
    .btn:hover .ic { color: var(--text-2); }
    .btn:active { transform: scale(0.98); }
    .btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    .btn-primary { background: var(--text); color: var(--deep); border-color: transparent; }
    .btn-primary .ic { color: var(--deep); }
    .btn-primary:hover { background: #ffffff; border-color: transparent; }
    .btn-quiet { background: transparent; border-color: transparent; color: var(--text-2); }
    .btn-quiet:hover { background: var(--raised); color: var(--text); }
    .btn-danger { background: transparent; border-color: transparent; color: var(--text-2); }
    .btn-danger:hover { background: rgba(229,72,77,0.12); color: var(--neg); }
    .btn-danger:hover .ic { color: var(--neg); }
    .btn-sm { height: 32px; padding: 0 12px; font-size: 13px; }
    .btn-icon { width: 36px; padding: 0; }

    .dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
    .dot-pos { background: var(--pos); }
    .dot-neg { background: var(--neg); }
    .dot-muted { background: var(--muted); opacity: 0.5; }
"""


LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Talenta Attendance · Sign in</title>
    <style>
    __BASE_CSS__
        body { display: flex; align-items: center; justify-content: center; padding: 24px; }
        .card {
            width: 100%; max-width: 360px;
            background: var(--surface); border: 1px solid var(--line); border-radius: 16px;
            padding: 32px;
        }
        .brand { display: flex; align-items: center; gap: 10px; margin-bottom: 28px; }
        .brand .mark {
            width: 32px; height: 32px; border-radius: 8px; background: var(--raised);
            border: 1px solid var(--line); display: flex; align-items: center; justify-content: center;
        }
        .brand .mark .ic { color: var(--accent); }
        .brand .name { font-size: 15px; font-weight: 500; }
        .brand .name span { color: var(--muted); font-weight: 400; }
        h1 { font-size: 20px; font-weight: 500; line-height: 1.2; margin-bottom: 6px; }
        p.sub { color: var(--text-2); font-size: 14px; margin-bottom: 24px; }
        label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 8px; }
        input {
            width: 100%; height: 40px; padding: 0 12px; border-radius: 8px;
            border: 1px solid var(--line); background: var(--raised); color: var(--text);
            font: 400 14px/1 'Geist', sans-serif; outline: none; margin-bottom: 20px;
            transition: border-color 140ms var(--ease);
        }
        input:focus { border-color: var(--accent); }
        .btn-primary { width: 100%; height: 40px; }
        .error {
            background: rgba(229,72,77,0.1); border: 1px solid rgba(229,72,77,0.3); color: #f0a7a9;
            padding: 10px 12px; border-radius: 8px; margin-bottom: 20px; font-size: 13px;
        }
    </style>
</head>
<body>
    <form class="card" method="POST" action="/login">
        <div class="brand">
            <div class="mark"><svg class="ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg></div>
            <div class="name">Talenta <span>Attendance</span></div>
        </div>
        <h1>Sign in</h1>
        <p class="sub">Manage automatic clock in and out across your accounts</p>
        <!--ERROR-->
        <label for="password">Admin password</label>
        <input type="password" id="password" name="password" autofocus required>
        <button type="submit" class="btn btn-primary">
            <svg class="ic" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" x2="3" y1="12" y2="12"/></svg>
            Sign in
        </button>
    </form>
</body>
</html>""".replace('__BASE_CSS__', _BASE_CSS)


ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Talenta Attendance</title>
    <style>
    __BASE_CSS__
        /* top bar */
        .topbar {
            position: sticky; top: 0; z-index: 20;
            height: 56px; display: flex; align-items: center; justify-content: space-between;
            padding: 0 24px; background: var(--deep); border-bottom: 1px solid var(--line);
        }
        .brand { display: flex; align-items: center; gap: 10px; }
        .brand .mark {
            width: 28px; height: 28px; border-radius: 7px; background: var(--raised);
            border: 1px solid var(--line); display: flex; align-items: center; justify-content: center;
        }
        .brand .mark .ic { color: var(--accent); }
        .brand .name { font-size: 15px; font-weight: 500; }
        .brand .name span { color: var(--muted); font-weight: 400; }
        .topbar-actions { display: flex; align-items: center; gap: 8px; }

        .page { max-width: 1280px; margin: 0 auto; padding: 32px 24px 64px; }
        .page-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 24px; }
        .page-title { font-size: 28px; font-weight: 500; line-height: 1.15; }
        .page-meta { font-size: 13px; color: var(--muted); margin-top: 4px; }

        /* account grid */
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; margin-bottom: 48px; }
        .card {
            background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
            padding: 20px; display: flex; flex-direction: column; gap: 16px;
            transition: border-color 140ms var(--ease);
            animation: rise 400ms var(--ease) both;
        }
        .card:hover { border-color: var(--line-2); }
        @keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

        .ac-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
        .ac-id { display: flex; align-items: center; gap: 10px; min-width: 0; }
        .ac-name { font-size: 15px; font-weight: 500; }
        .ac-mail { font-family: var(--mono); font-size: 12px; color: var(--muted); margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .ac-state { display: inline-flex; align-items: center; gap: 7px; font-size: 12px; color: var(--text-2); white-space: nowrap; }

        /* the moment: today's punch card */
        .punch { display: grid; grid-template-columns: 1fr 1fr 1fr; background: var(--raised); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
        .punch-col { padding: 12px 14px; }
        .punch-col + .punch-col { border-left: 1px solid var(--line); }
        .punch-label { font-size: 11px; color: var(--muted); margin-bottom: 7px; }
        .punch-val { display: flex; align-items: center; gap: 7px; font-family: var(--mono); font-size: 16px; color: var(--text); font-variant-numeric: tabular-nums; }
        .punch-val.na { color: var(--muted); }
        .shift-chip { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; color: var(--text); }

        .ac-sched { font-family: var(--mono); font-size: 12px; color: var(--muted); }
        .ac-sched .arrow { color: var(--line-2); margin: 0 2px; }
        .ac-sched .sep { margin: 0 6px; color: var(--line-2); }

        .ac-actions { display: flex; gap: 8px; }
        .ac-actions .btn { flex: 1; }
        .ac-foot { display: flex; gap: 8px; padding-top: 4px; border-top: 1px solid var(--line); }

        /* activity */
        .section-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
        .section-title { font-size: 16px; font-weight: 500; }
        .log {
            background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
            overflow: hidden;
        }
        .log-row { display: grid; grid-template-columns: 16px 140px 88px 1fr auto; align-items: center; gap: 12px; padding: 12px 16px; font-size: 13px; }
        .log-row + .log-row { border-top: 1px solid var(--line); }
        .log-acct { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .log-action { color: var(--text-2); }
        .log-msg { color: var(--text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .log-msg .trig { color: var(--muted); }
        .log-time { font-family: var(--mono); font-size: 12px; color: var(--muted); white-space: nowrap; }

        .empty { padding: 48px 24px; text-align: center; color: var(--muted); font-size: 14px; }
        .spin { width: 20px; height: 20px; border: 2px solid var(--line-2); border-top-color: var(--text-2); border-radius: 50%; animation: spin 700ms linear infinite; margin: 48px auto; }
        .spin-sm { display: inline-block; width: 14px; height: 14px; border: 2px solid var(--line-2); border-top-color: var(--text-2); border-radius: 50%; animation: spin 700ms linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* modal */
        .overlay { position: fixed; inset: 0; background: rgba(8,8,9,0.72); display: none; align-items: flex-start; justify-content: center; z-index: 50; padding: 40px 16px; overflow-y: auto; }
        .overlay.show { display: flex; animation: fade 160ms var(--ease); }
        @keyframes fade { from { opacity: 0; } to { opacity: 1; } }
        .modal { width: 100%; max-width: 600px; background: var(--surface); border: 1px solid var(--line-2); border-radius: 16px; padding: 24px; animation: rise 240ms var(--ease); }
        .modal-wide { max-width: 1040px; }
        .modal-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
        .modal h2 { font-size: 18px; font-weight: 500; }
        .modal .hint { color: var(--text-2); font-size: 13px; margin-top: 4px; }

        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .field { display: flex; flex-direction: column; }
        .field.full { grid-column: 1 / -1; }
        .field label { font-size: 12px; color: var(--muted); margin-bottom: 7px; }
        .field input {
            height: 38px; padding: 0 12px; border-radius: 8px; border: 1px solid var(--line);
            background: var(--raised); color: var(--text); font: 400 14px/1 'Geist', sans-serif; outline: none;
            transition: border-color 140ms var(--ease);
        }
        .field input::placeholder { color: var(--muted); }
        .field input:focus { border-color: var(--accent); }
        .group-label { grid-column: 1 / -1; font-size: 12px; color: var(--muted); padding-top: 12px; margin-top: 4px; border-top: 1px solid var(--line); }
        .switch { display: flex; align-items: center; gap: 10px; align-self: end; height: 38px; }
        .switch input { width: 16px; height: 16px; accent-color: var(--accent); }
        .switch label { font-size: 14px; color: var(--text); margin: 0; }
        .modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }

        /* calendar */
        .cal-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
        .cal-nav { display: flex; align-items: center; gap: 8px; }
        .cal-month { font-family: var(--mono); font-size: 16px; color: var(--text); min-width: 160px; }
        .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
        .cal-dow { text-align: left; padding: 4px 8px; font-size: 12px; color: var(--muted); }
        .cal-cell { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; min-height: 76px; padding: 8px; display: flex; flex-direction: column; gap: 6px; }
        .cal-cell.other { opacity: 0.4; }
        .cal-cell.today { border-color: var(--accent); }
        .cal-day { font-family: var(--mono); font-size: 13px; color: var(--text-2); }
        .cal-cell.today .cal-day { color: var(--accent); }
        .cal-shift { font-size: 11px; padding: 3px 7px; border-radius: 5px; width: fit-content; }
        .s-wfa { color: #8fe3bd; background: rgba(76,195,138,0.14); }
        .s-wfo { color: #f0c07a; background: rgba(232,163,61,0.16); }
        .s-hol { color: #eda0a3; background: rgba(229,72,77,0.16); }
        .s-off { color: var(--muted); background: rgba(237,237,237,0.06); }
        .cal-legend { display: flex; flex-wrap: wrap; gap: 16px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line); }
        .legend-item { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-2); }
        .legend-swatch { width: 10px; height: 10px; border-radius: 3px; }

        /* toast */
        .toast { position: fixed; bottom: 24px; right: 24px; max-width: 360px; background: var(--raised); border: 1px solid var(--line-2); border-left: 2px solid var(--muted); color: var(--text); padding: 12px 16px; border-radius: 8px; z-index: 100; opacity: 0; transform: translateY(8px); transition: opacity 180ms var(--ease), transform 180ms var(--ease); font-size: 13px; pointer-events: none; }
        .toast.show { opacity: 1; transform: none; }
        .toast.ok { border-left-color: var(--pos); }
        .toast.err { border-left-color: var(--neg); }

        .credit { text-align: center; font-size: 12px; color: var(--muted); padding: 24px; }
        .credit a { color: var(--text-2); text-decoration: none; }

        /* tablets */
        @media (max-width: 640px) {
            .grid { grid-template-columns: 1fr; }
        }

        /* phones */
        @media (max-width: 560px) {
            .topbar { padding: 0 16px; }
            .page { padding: 20px 16px 48px; }
            .page-head { flex-direction: column; align-items: stretch; gap: 16px; }
            .page-title { font-size: 24px; }
            .page-head .btn-primary { width: 100%; }

            .form-grid { grid-template-columns: 1fr; }
            .log-row { grid-template-columns: 16px 1fr auto; }
            .log-action, .log-msg { display: none; }

            .overlay { padding: 12px 8px; }
            .modal { padding: 20px; border-radius: 14px; }

            .cal-head { flex-wrap: wrap; }
            .cal-month { min-width: 0; font-size: 15px; }
            .cal-grid { gap: 4px; }
            .cal-dow { padding: 4px; font-size: 11px; }
            .cal-cell { min-height: 56px; padding: 6px; border-radius: 6px; gap: 4px; }
            .cal-day { font-size: 12px; }
            .cal-shift { font-size: 10px; padding: 2px 5px; }

            .punch-col { padding: 10px; }
            .punch-val { font-size: 15px; }

            .toast { left: 12px; right: 12px; bottom: 12px; max-width: none; }
        }

        /* small phones */
        @media (max-width: 400px) {
            .brand .name span { display: none; }
            .ac-actions { flex-wrap: wrap; }
            .ac-actions .btn { flex: 1 1 calc(50% - 4px); }
        }
    </style>
</head>
<body>
    <div class="topbar">
        <div class="brand">
            <div class="mark"><svg class="ic" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg></div>
            <div class="name">Talenta <span>Attendance</span></div>
        </div>
        <div class="topbar-actions">
            <button class="btn btn-quiet btn-sm" onclick="loadAll()" title="Refresh" id="refreshBtn"></button>
            <a class="btn btn-quiet btn-sm" href="/logout">Log out</a>
        </div>
    </div>

    <div class="page">
        <div class="page-head">
            <div>
                <div class="page-title">Accounts</div>
                <div class="page-meta" id="pageMeta">Loading</div>
            </div>
            <button class="btn btn-primary" onclick="openCreate()" id="addBtn">Add account</button>
        </div>

        <div class="grid" id="cards"><div class="spin"></div></div>

        <div class="section-head"><div class="section-title">Activity</div></div>
        <div class="log" id="logs"><div class="empty">No activity yet</div></div>
    </div>

    <!-- Account form modal -->
    <div class="overlay" id="formOverlay">
        <div class="modal">
            <div class="modal-head">
                <div>
                    <h2 id="formTitle">Add account</h2>
                    <div class="hint">Credentials are stored on the server and used to sign in to Talenta</div>
                </div>
                <button class="btn btn-quiet btn-icon btn-sm" onclick="closeForm()" id="formClose"></button>
            </div>
            <form id="accountForm" onsubmit="return submitForm(event)">
                <input type="hidden" id="f_id">
                <div class="form-grid">
                    <div class="field"><label>Label</label><input id="f_label" required placeholder="Budi"></div>
                    <div class="field"><label>Email</label><input id="f_email" type="email" placeholder="name@company.com"></div>
                    <div class="field"><label>Password</label><input id="f_password" type="password" placeholder="Talenta password"></div>
                    <div class="field full"><label>Manual cookie (fallback)</label><input id="f_cookies" placeholder="PHPSESSID= — leave blank if using email and password"></div>

                    <div class="group-label">Schedule</div>
                    <div class="field"><label>Clock in</label><input id="f_clock_in_time" placeholder="08:50"></div>
                    <div class="field"><label>Clock out</label><input id="f_clock_out_time" placeholder="18:15"></div>
                    <div class="field"><label>Random jitter (minutes)</label><input id="f_jitter_minutes" type="number" min="0" value="10"></div>
                    <div class="switch"><input type="checkbox" id="f_wfa_only" checked><label for="f_wfa_only">WFA only, skip WFO days</label></div>
                    <div class="switch"><input type="checkbox" id="f_enabled" checked><label for="f_enabled">Automation enabled</label></div>

                    <div class="group-label">Location</div>
                    <div class="field"><label>Latitude</label><input id="f_latitude" placeholder="-6.000"></div>
                    <div class="field"><label>Longitude</label><input id="f_longitude" placeholder="107.000"></div>

                    <div class="group-label">Schedule API — needed for the shift viewer</div>
                    <div class="field"><label>Organisation ID</label><input id="f_mekari_org_id" placeholder="2767"></div>
                    <div class="field"><label>Organisation user ID</label><input id="f_mekari_org_user_id" placeholder="3939862"></div>
                    <div class="field full"><label>Bearer token</label><input id="f_bearer_token" placeholder="Auto-extracted from login if blank"></div>

                    <div class="group-label">Telegram notifications</div>
                    <div class="field"><label>Bot token</label><input id="f_telegram_bot_token" placeholder="123:ABC"></div>
                    <div class="field"><label>Chat ID</label><input id="f_telegram_chat_id" placeholder="123456789"></div>
                </div>
                <div class="modal-actions">
                    <button type="button" class="btn btn-quiet" onclick="closeForm()">Cancel</button>
                    <button type="submit" class="btn btn-primary" id="formSubmit">Save</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Schedule modal -->
    <div class="overlay" id="calOverlay">
        <div class="modal modal-wide">
            <div class="modal-head">
                <div>
                    <h2 id="calTitle">Schedule</h2>
                    <div class="hint" id="calSub"></div>
                </div>
                <button class="btn btn-quiet btn-icon btn-sm" onclick="closeCal()" id="calClose"></button>
            </div>
            <div class="cal-head">
                <div class="cal-month" id="calMonth"></div>
                <div class="cal-nav">
                    <button class="btn btn-quiet btn-icon btn-sm" onclick="calPrev()" id="calPrevBtn"></button>
                    <button class="btn btn-quiet btn-sm" onclick="calToday()">Today</button>
                    <button class="btn btn-quiet btn-icon btn-sm" onclick="calNext()" id="calNextBtn"></button>
                </div>
            </div>
            <div id="calBody"><div class="spin"></div></div>
            <div class="cal-legend">
                <div class="legend-item"><span class="legend-swatch" style="background:rgba(76,195,138,0.5)"></span>WFA</div>
                <div class="legend-item"><span class="legend-swatch" style="background:rgba(232,163,61,0.6)"></span>WFO</div>
                <div class="legend-item"><span class="legend-swatch" style="background:rgba(229,72,77,0.5)"></span>Holiday</div>
                <div class="legend-item"><span class="legend-swatch" style="background:rgba(237,237,237,0.18)"></span>Day off</div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

<script>
const ICONS = {
  refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  login: '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" x2="3" y1="12" y2="12"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
  calendar: '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/><path d="M8 2v4"/><path d="M16 2v4"/>',
  power: '<path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.77.04"/>',
  pencil: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  left: '<path d="m15 18-6-6 6-6"/>',
  right: '<path d="m9 18 6-6-6-6"/>'
};
function icon(name, size){ size = size || 16; return '<svg class="ic" width="'+size+'" height="'+size+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'+(ICONS[name]||'')+'</svg>'; }

// place static icons
document.getElementById('refreshBtn').innerHTML = icon('refresh') + 'Refresh';
document.getElementById('addBtn').innerHTML = icon('plus') + 'Add account';
document.getElementById('formClose').innerHTML = icon('x');
document.getElementById('calClose').innerHTML = icon('x');
document.getElementById('calPrevBtn').innerHTML = icon('left');
document.getElementById('calNextBtn').innerHTML = icon('right');

let ACCOUNTS = [];

function toast(msg, ok){
  if (ok === undefined) ok = true;
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'toast show ' + (ok ? 'ok' : 'err');
  setTimeout(function(){ t.className = 'toast'; }, 3200);
}

async function api(url, opts){
  const res = await fetch(url, Object.assign({headers:{'Content-Type':'application/json'}}, opts || {}));
  if (res.status === 401) { window.location = '/login'; throw new Error('unauthorized'); }
  const data = await res.json().catch(function(){ return {}; });
  if (!res.ok || data.success === false) { throw new Error(data.message || data.error || ('HTTP ' + res.status)); }
  return data;
}

function escapeHtml(s){ return (s||'').replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }

function shiftClass(shift){ if(!shift) return 's-off'; const s = shift.toLowerCase(); if(s==='wfa') return 's-wfa'; if(s==='wfo') return 's-wfo'; if(s.indexOf('holiday')>-1) return 's-hol'; return 's-off'; }

function cardHtml(a){
  const rule = a.wfa_only ? 'WFA only' : 'WFA and WFO';
  return '<div class="card" style="animation-delay:' + (Math.min(ACCOUNTS.indexOf(a),6) * 40) + 'ms">'
    + '<div class="ac-head">'
      + '<div class="ac-id"><span class="dot ' + (a.enabled?'dot-pos':'dot-muted') + '"></span>'
        + '<div style="min-width:0"><div class="ac-name">' + escapeHtml(a.label) + '</div>'
        + '<div class="ac-mail">' + escapeHtml(a.email || 'cookie auth') + '</div></div></div>'
      + '<span class="ac-state">' + (a.enabled ? 'Enabled' : 'Disabled') + '</span>'
    + '</div>'
    + '<div class="punch">'
      + '<div class="punch-col"><div class="punch-label">Clock in</div><div class="punch-val na" id="pin-' + a.id + '"><span class="spin-sm"></span></div></div>'
      + '<div class="punch-col"><div class="punch-label">Clock out</div><div class="punch-val na" id="pout-' + a.id + '"><span class="spin-sm"></span></div></div>'
      + '<div class="punch-col"><div class="punch-label">Shift today</div><div class="shift-chip" id="pshift-' + a.id + '"><span class="spin-sm"></span></div></div>'
    + '</div>'
    + '<div class="ac-sched">' + a.clock_in_time + '<span class="arrow">→</span>' + a.clock_out_time
      + '<span class="sep">·</span>±' + a.jitter_minutes + 'm<span class="sep">·</span>' + rule + '</div>'
    + '<div class="ac-actions">'
      + '<button class="btn btn-sm" onclick="doClock(' + a.id + ',\'clockin\')">' + icon('login') + 'Clock in</button>'
      + '<button class="btn btn-sm" onclick="doClock(' + a.id + ',\'clockout\')">' + icon('logout') + 'Clock out</button>'
      + '<button class="btn btn-sm" onclick="openSchedule(' + a.id + ')">' + icon('calendar') + 'Schedule</button>'
    + '</div>'
    + '<div class="ac-foot">'
      + '<button class="btn btn-quiet btn-sm" onclick="toggleEnabled(' + a.id + ',' + (a.enabled?0:1) + ')">' + icon('power') + (a.enabled?'Disable':'Enable') + '</button>'
      + '<button class="btn btn-quiet btn-sm" onclick="openEdit(' + a.id + ')">' + icon('pencil') + 'Edit</button>'
      + '<button class="btn btn-danger btn-sm" onclick="delAccount(' + a.id + ')">' + icon('trash') + 'Delete</button>'
    + '</div></div>';
}

async function loadAll(){
  try {
    const data = await api('/api/accounts');
    ACCOUNTS = data.accounts;
    const enabled = ACCOUNTS.filter(function(a){ return a.enabled; }).length;
    document.getElementById('pageMeta').textContent = ACCOUNTS.length + (ACCOUNTS.length===1?' account':' accounts') + ' · ' + enabled + ' enabled';
    const cards = document.getElementById('cards');
    if (!ACCOUNTS.length) { cards.innerHTML = '<div class="empty">No accounts yet. Add one to start automating attendance.</div>'; }
    else { cards.innerHTML = ACCOUNTS.map(cardHtml).join(''); ACCOUNTS.forEach(function(a){ loadToday(a.id); }); }
    loadLogs();
  } catch (e) { toast(e.message, false); }
}

function timePart(iso){ if(!iso) return null; const m = String(iso).match(/T(\d{2}:\d{2})/); return m ? m[1] : null; }

async function loadToday(id){
  const pin = document.getElementById('pin-' + id);
  const pout = document.getElementById('pout-' + id);
  const psh = document.getElementById('pshift-' + id);
  if (pin) { pin.className = 'punch-val na'; pin.innerHTML = '<span class="spin-sm"></span>'; }
  if (pout) { pout.className = 'punch-val na'; pout.innerHTML = '<span class="spin-sm"></span>'; }
  if (psh) { psh.innerHTML = '<span class="spin-sm"></span>'; }
  try {
    const d = await api('/api/accounts/' + id + '/today');
    const ti = timePart(d.clock_in_at), to = timePart(d.clock_out_at);
    if (pin) {
      if (d.clocked_in) { pin.className = 'punch-val'; pin.innerHTML = '<span class="dot dot-pos"></span>' + (ti || 'done'); }
      else { pin.className = 'punch-val na'; pin.innerHTML = '<span class="dot dot-muted"></span>—'; }
    }
    if (pout) {
      if (d.clocked_out) { pout.className = 'punch-val'; pout.innerHTML = '<span class="dot dot-pos"></span>' + (to || 'done'); }
      else { pout.className = 'punch-val na'; pout.innerHTML = '<span class="dot dot-muted"></span>—'; }
    }
    if (psh) {
      if (d.shift) { psh.innerHTML = '<span class="dot" style="background:' + shiftColor(d.shift) + '"></span>' + escapeHtml(d.shift); }
      else { psh.innerHTML = '<span class="dot dot-muted"></span>unknown'; }
    }
  } catch (e) {
    if (pin) pin.innerHTML = '<span class="dot dot-muted"></span>n/a';
    if (pout) pout.innerHTML = '<span class="dot dot-muted"></span>n/a';
    if (psh) psh.innerHTML = '<span class="dot dot-muted"></span>n/a';
  }
}

function shiftColor(shift){ const s = (shift||'').toLowerCase(); if(s==='wfa') return '#4cc38a'; if(s==='wfo') return '#e8a33d'; if(s.indexOf('holiday')>-1) return '#e5484d'; return '#85858b'; }

async function loadLogs(){
  try {
    const d = await api('/api/logs?limit=40');
    const box = document.getElementById('logs');
    if (!d.logs.length) { box.innerHTML = '<div class="empty">No activity yet</div>'; return; }
    box.innerHTML = d.logs.map(function(l){
      const cls = l.status === 'success' ? 'dot-pos' : (l.status === 'failed' ? 'dot-neg' : 'dot-muted');
      return '<div class="log-row">'
        + '<span class="dot ' + cls + '"></span>'
        + '<span class="log-acct">' + escapeHtml(l.account_label || '—') + '</span>'
        + '<span class="log-action">' + (l.action === 'clockout' ? 'Clock out' : 'Clock in') + '</span>'
        + '<span class="log-msg">' + escapeHtml(l.message) + ' <span class="trig">· ' + escapeHtml(l.trigger) + '</span></span>'
        + '<span class="log-time">' + (l.created_at || '').replace('T', ' ') + '</span>'
      + '</div>';
    }).join('');
  } catch (e) { /* ignore */ }
}

async function doClock(id, action){
  if (!confirm((action === 'clockout' ? 'Clock out' : 'Clock in') + ' now for this account?')) return;
  try {
    const d = await api('/api/accounts/' + id + '/' + action, {method:'POST'});
    toast(d.message || 'Done', d.data ? d.data.success : true);
    loadToday(id); loadLogs();
  } catch (e) { toast(e.message, false); }
}

async function toggleEnabled(id, enabled){
  try {
    await api('/api/accounts/' + id + '/enabled', {method:'POST', body: JSON.stringify({enabled: !!enabled})});
    toast(enabled ? 'Automation enabled' : 'Automation disabled');
    loadAll();
  } catch (e) { toast(e.message, false); }
}

async function delAccount(id){
  const a = ACCOUNTS.find(function(x){ return x.id === id; });
  if (!confirm('Delete account "' + (a ? a.label : id) + '"? This cannot be undone.')) return;
  try { await api('/api/accounts/' + id, {method:'DELETE'}); scheduleCache.clearAccount(id); toast('Account deleted'); loadAll(); }
  catch (e) { toast(e.message, false); }
}

const FIELDS = ['label','email','password','cookies','clock_in_time','clock_out_time','jitter_minutes','latitude','longitude','mekari_org_id','mekari_org_user_id','bearer_token','telegram_bot_token','telegram_chat_id'];

function openCreate(){
  document.getElementById('formTitle').textContent = 'Add account';
  document.getElementById('f_id').value = '';
  FIELDS.forEach(function(f){ document.getElementById('f_' + f).value = ''; });
  document.getElementById('f_clock_in_time').value = '08:50';
  document.getElementById('f_clock_out_time').value = '18:15';
  document.getElementById('f_jitter_minutes').value = '10';
  document.getElementById('f_latitude').value = '-6.000';
  document.getElementById('f_longitude').value = '107.000';
  document.getElementById('f_wfa_only').checked = true;
  document.getElementById('f_enabled').checked = true;
  document.getElementById('f_password').placeholder = 'Talenta password';
  document.getElementById('f_cookies').placeholder = 'PHPSESSID=';
  document.getElementById('f_bearer_token').placeholder = 'Auto-extracted from login if blank';
  document.getElementById('f_telegram_bot_token').placeholder = '123:ABC';
  document.getElementById('formOverlay').classList.add('show');
}

function openEdit(id){
  const a = ACCOUNTS.find(function(x){ return x.id === id; });
  if (!a) return;
  document.getElementById('formTitle').textContent = 'Edit ' + a.label;
  document.getElementById('f_id').value = a.id;
  document.getElementById('f_label').value = a.label || '';
  document.getElementById('f_email').value = a.email || '';
  document.getElementById('f_clock_in_time').value = a.clock_in_time || '';
  document.getElementById('f_clock_out_time').value = a.clock_out_time || '';
  document.getElementById('f_jitter_minutes').value = a.jitter_minutes;
  document.getElementById('f_latitude').value = a.latitude || '';
  document.getElementById('f_longitude').value = a.longitude || '';
  document.getElementById('f_mekari_org_id').value = a.mekari_org_id || '';
  document.getElementById('f_mekari_org_user_id').value = a.mekari_org_user_id || '';
  document.getElementById('f_telegram_chat_id').value = a.telegram_chat_id || '';
  document.getElementById('f_wfa_only').checked = !!a.wfa_only;
  document.getElementById('f_enabled').checked = !!a.enabled;
  document.getElementById('f_password').value = '';
  document.getElementById('f_cookies').value = '';
  document.getElementById('f_bearer_token').value = '';
  document.getElementById('f_telegram_bot_token').value = '';
  const keep = ' — leave blank to keep';
  document.getElementById('f_password').placeholder = a.has_password ? ('Saved' + keep) : 'Talenta password';
  document.getElementById('f_cookies').placeholder = a.has_cookies ? ('Saved' + keep) : 'PHPSESSID=';
  document.getElementById('f_bearer_token').placeholder = a.has_bearer_token ? ('Saved' + keep) : 'Auto-extracted if blank';
  document.getElementById('f_telegram_bot_token').placeholder = a.has_telegram_bot_token ? ('Saved' + keep) : '123:ABC';
  document.getElementById('formOverlay').classList.add('show');
}

function closeForm(){ document.getElementById('formOverlay').classList.remove('show'); }

async function submitForm(ev){
  ev.preventDefault();
  const id = document.getElementById('f_id').value;
  const payload = {
    wfa_only: document.getElementById('f_wfa_only').checked,
    enabled: document.getElementById('f_enabled').checked
  };
  FIELDS.forEach(function(f){ payload[f] = document.getElementById('f_' + f).value; });
  if (id) { ['password','cookies','bearer_token','telegram_bot_token'].forEach(function(s){ if (!payload[s]) delete payload[s]; }); }
  try {
    if (id) {
      await api('/api/accounts/' + id, {method:'PUT', body: JSON.stringify(payload)});
      scheduleCache.clearAccount(parseInt(id, 10));  // its schedule may have changed
      toast('Changes saved');
    } else {
      await api('/api/accounts', {method:'POST', body: JSON.stringify(payload)}); toast('Account created');
    }
    closeForm(); loadAll();
  } catch (e) { toast(e.message, false); }
  return false;
}

/* calendar */
let calAccountId = null, calDate = new Date();
const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
const DOW = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

// Per-month schedule cache, persisted in localStorage. A month that has been
// opened is kept for one day so switching back to it does not re-fetch.
const scheduleCache = {
  KEY: 'talentaScheduleCache',
  TTL: 24 * 60 * 60 * 1000,
  _data: null,
  _load: function(){
    if (this._data) return;
    try { this._data = JSON.parse(localStorage.getItem(this.KEY) || '{}'); }
    catch (e) { this._data = {}; }
  },
  _save: function(){ try { localStorage.setItem(this.KEY, JSON.stringify(this._data)); } catch (e) {} },
  get: function(key){
    this._load();
    const entry = this._data[key];
    if (!entry) return null;
    if (Date.now() - entry.t > this.TTL) { delete this._data[key]; this._save(); return null; }
    return entry.v;
  },
  set: function(key, value){ this._load(); this._data[key] = { v: value, t: Date.now() }; this._save(); },
  clearAccount: function(accountId){
    this._load();
    const prefix = accountId + ':';
    Object.keys(this._data).forEach(function(k){ if (k.indexOf(prefix) === 0) delete this._data[k]; }, this);
    this._save();
  },
  clear: function(){ this._data = {}; try { localStorage.removeItem(this.KEY); } catch (e) {} }
};

function fmt(d){ return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); }

function openSchedule(id){
  calAccountId = id; calDate = new Date();
  const a = ACCOUNTS.find(function(x){ return x.id === id; });
  document.getElementById('calTitle').textContent = 'Schedule';
  document.getElementById('calSub').textContent = a ? (a.label + (a.email ? ' · ' + a.email : '')) : '';
  document.getElementById('calOverlay').classList.add('show');
  renderCal();
}
function closeCal(){ document.getElementById('calOverlay').classList.remove('show'); }
function calPrev(){ calDate.setMonth(calDate.getMonth()-1); renderCal(); }
function calNext(){ calDate.setMonth(calDate.getMonth()+1); renderCal(); }
function calToday(){ calDate = new Date(); renderCal(); }

async function renderCal(){
  const y = calDate.getFullYear(), m = calDate.getMonth();
  document.getElementById('calMonth').textContent = MONTHS[m] + ' ' + y;
  const body = document.getElementById('calBody');
  body.innerHTML = '<div class="spin"></div>';
  const first = new Date(y, m, 1), last = new Date(y, m+1, 0);
  const start = new Date(first); start.setDate(start.getDate() - start.getDay());
  const end = new Date(last); end.setDate(end.getDate() + (6 - end.getDay()));
  const cacheKey = calAccountId + ':' + fmt(start) + '_' + fmt(end);
  let map = {};
  const cached = scheduleCache.get(cacheKey);
  if (cached) {
    map = cached;
  } else {
    try {
      const d = await api('/api/accounts/' + calAccountId + '/schedule?start_date=' + fmt(start) + '&end_date=' + fmt(end));
      (d.schedule || []).forEach(function(it){ map[it.date] = it; });
      scheduleCache.set(cacheKey, map);
    } catch (e) {
      body.innerHTML = '<div class="empty">' + escapeHtml(e.message) + '<br><br>Set the Mekari Organisation IDs on this account to enable the schedule viewer.</div>';
      return;
    }
  }
  let html = '<div class="cal-grid">' + DOW.map(function(d){ return '<div class="cal-dow">' + d + '</div>'; }).join('');
  const today = fmt(new Date());
  let cur = new Date(start);
  while (cur <= end) {
    const ds = fmt(cur), inMonth = cur.getMonth() === m, shift = map[ds] ? map[ds].shift : null;
    let cls = 'cal-cell'; if (!inMonth) cls += ' other'; if (ds === today) cls += ' today';
    html += '<div class="' + cls + '"><div class="cal-day">' + cur.getDate() + '</div>'
      + (shift ? '<div class="cal-shift ' + shiftClass(shift) + '">' + escapeHtml(shift) + '</div>' : '') + '</div>';
    cur.setDate(cur.getDate() + 1);
  }
  html += '</div>';
  body.innerHTML = html;
}

document.getElementById('formOverlay').addEventListener('click', function(e){ if (e.target.id === 'formOverlay') closeForm(); });
document.getElementById('calOverlay').addEventListener('click', function(e){ if (e.target.id === 'calOverlay') closeCal(); });
document.addEventListener('keydown', function(e){ if (e.key === 'Escape') { closeForm(); closeCal(); } });

loadAll();
</script>
</body>
</html>""".replace('__BASE_CSS__', _BASE_CSS)
