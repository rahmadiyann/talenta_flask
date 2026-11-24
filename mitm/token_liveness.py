"""
Poll a captured Talenta mobile access token until it dies, to measure its
lifetime. Reads the token from mitm/state/token.txt.

    .venv/bin/python mitm/token_liveness.py [interval_seconds]

Logs each probe to mitm/state/liveness.log and stdout. Exits when the token
returns 401 (dead) or after too many network errors.
"""
import datetime
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(HERE, "state", "token.txt")
LOG_FILE = os.path.join(HERE, "state", "liveness.log")

INTERVAL = int(sys.argv[1]) if len(sys.argv) > 1 else 60

# Lightweight authenticated endpoint; 200 = alive, 401 = token dead.
URL = "https://api.mekari.com/internal/talenta-mobile/v1/dashboard/user"
HEADERS = {
    "Authorization": "Bearer " + open(TOKEN_FILE).read().strip(),
    "User-Agent": "Talenta/13740 CFNetwork/3860.100.1 Darwin/25.0.0",
    "x-app-version": "2.126.0",
    "x-device-model": "iPhone14,2",
    "x-os-version": "iOS 18.7",
    "Accept": "*/*",
}

start = time.time()


def log(msg):
    elapsed = int(time.time() - start)
    line = "%s  +%5ds (%4.2fh)  %s" % (
        datetime.datetime.now().strftime("%H:%M:%S"), elapsed, elapsed / 3600.0, msg
    )
    print(line, flush=True)
    with open(LOG_FILE, "a") as fh:
        fh.write(line + "\n")


tok = HEADERS["Authorization"].split(" ", 1)[1]
log("START polling every %ss | token %s… (%d chars)" % (INTERVAL, tok[:13], len(tok)))

errors = 0
while True:
    try:
        r = requests.get(URL, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            log("alive (200)")
            errors = 0
        elif r.status_code == 401:
            secs = int(time.time() - start)
            log("DEAD (401) — token lived ~%ds = %.2f min = %.2f h" % (
                secs, secs / 60.0, secs / 3600.0))
            log("response: " + r.text[:120])
            break
        else:
            log("unexpected %d: %s" % (r.status_code, r.text[:100]))
            errors = 0
    except Exception as error:
        errors += 1
        log("neterr (%d/5): %s" % (errors, repr(error)[:70]))
        if errors >= 5:
            log("giving up after 5 consecutive network errors")
            break
    time.sleep(INTERVAL)
