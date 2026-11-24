"""
mitmproxy addon — capture Talenta / Mekari mobile API traffic.

Only flows to mekari.com / talenta.co reach here (see allow_hosts in run.sh), so
other apps on the phone keep working and are never decrypted. Every captured
request+response is written to:

  state/capture.log    - one readable line per request (tail -f this)
  state/capture.jsonl  - full request + response (headers + body) as JSON

⚠️  capture.jsonl contains auth tokens and session data — treat it like a
password. Do not commit it; delete it when done.
"""

import json
import os
import time

from mitmproxy import http

STATE_DIR = os.environ.get(
    "MITM_STATE_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
)
os.makedirs(STATE_DIR, exist_ok=True)
LOG_PATH = os.path.join(STATE_DIR, "capture.log")
JSONL_PATH = os.path.join(STATE_DIR, "capture.jsonl")

# Requests whose URL contains any of these are the ones we actually want (clock
# in/out, schedule, auth). They get a ★ in the log. Everything to the allowed
# hosts is still captured — this only flags the interesting ones.
INTERESTING = (
    "attendance", "live-attendance", "clock", "checkin", "check-in",
    "checkout", "check-out", "schedule", "shift", "roster",
    "login", "auth", "token", "oauth", "sso", "session",
    "employee", "/me", "profile",
)

# Bodies can be large (HTML pages); cap what we store.
BODY_LIMIT = 300_000


def _body(message) -> str:
    """Best-effort decoded text body, or a size marker for binary content."""
    try:
        text = message.get_text(strict=False)
        if text is not None:
            return text[:BODY_LIMIT]
    except Exception:
        pass
    try:
        raw = message.raw_content or b""
        return f"<binary {len(raw)} bytes>"
    except Exception:
        return ""


def response(flow: http.HTTPFlow) -> None:
    req = flow.request
    res = flow.response
    if res is None:
        return

    url = req.pretty_url
    interesting = any(k in url.lower() for k in INTERESTING)
    auth = req.headers.get("authorization", "")

    marker = "★" if interesting else " "
    line = f"{marker} {time.strftime('%H:%M:%S')} {req.method:6} {res.status_code} {url}"
    if auth:
        line += f"  [Authorization: {auth[:24]}…]"

    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception as error:
        print(f"[capture] could not write log: {error}")

    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "interesting": interesting,
        "request": {
            "method": req.method,
            "url": url,
            "host": req.pretty_host,
            "headers": dict(req.headers),
            "body": _body(req),
        },
        "response": {
            "status_code": res.status_code,
            "headers": dict(res.headers),
            "body": _body(res),
        },
    }
    try:
        with open(JSONL_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as error:
        print(f"[capture] could not write jsonl: {error}")
