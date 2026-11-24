"""One-off: replicate the Talenta MOBILE PKCE OAuth flow server-side to see how
the Bearer token is delivered. Run inside the container:
    docker compose exec talenta-scheduler python3 mitm/probe_oauth.py
"""
import base64
import hashlib
import os
import re
import requests
from urllib.parse import urlparse

from src.core import accounts

a = accounts.get_account(1)
EMAIL, PASSWORD = a["email"], a["password"]
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")

s = requests.Session()
s.headers.update({"User-Agent": UA})

verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
challenge = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode()).digest()
).rstrip(b"=").decode()

auth_params = {
    "client_id": "QOA8dzKDsDAO3a08",
    "response_type": "code",
    "scope": "sso:profile",
    "redirect_uri": "https://api.mekari.com/mobile-platform-oauth2-redirection",
    "code_challenge": challenge,
    "code_challenge_method": "s256",
}

TOKEN_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_")


def short(u):
    p = urlparse(u or "")
    return (p.netloc + p.path)[:55]


r = s.get("https://account.mekari.com/auth", params=auth_params,
          allow_redirects=True, timeout=30)
print("1) after /auth ->", r.status_code, short(r.url))
m = re.search(r'name="authenticity_token" value="([^"]+)"', r.text)
print("   authenticity_token found:", bool(m))
if not m:
    raise SystemExit("no authenticity token")

r = s.post(r.url, data={
    "utf8": "✓", "authenticity_token": m.group(1),
    "user[email]": EMAIL, "user[password]": PASSWORD, "no-captcha-token": "",
}, allow_redirects=False, timeout=30)
print("2) login POST ->", r.status_code, "| location:", short(r.headers.get("location")))

loc = r.headers.get("location")
code = None
for hop in range(8):
    if not loc:
        break
    # grab the authorization code from the redirect, don't let it get consumed
    if "code=" in loc:
        from urllib.parse import parse_qs
        code = parse_qs(urlparse(loc).query).get("code", [None])[0]
    rr = s.get(loc, allow_redirects=False, timeout=30)
    nloc = rr.headers.get("location", "")
    print("   hop%d: %s %s -> %s" % (hop, rr.status_code, short(loc), short(nloc)))
    loc = nloc

print("\n>>> authorization code:", code)
print("final cookies:", list(s.cookies.get_dict().keys()))

# Try exchanging the code (+PKCE verifier) at candidate token endpoints.
print("\n=== token-exchange attempts ===")
candidates = [
    "https://account.mekari.com/oauth/token",
    "https://api.mekari.com/oauth/token",
    "https://id.mekari.com/oauth/token",
    "https://account.mekari.com/token",
    "https://api.mekari.com/mobile-platform-oauth2-redirection",
]
payload = {
    "grant_type": "authorization_code",
    "code": code,
    "code_verifier": verifier,
    "client_id": "QOA8dzKDsDAO3a08",
    "redirect_uri": "https://api.mekari.com/mobile-platform-oauth2-redirection",
}
for url in candidates:
    try:
        tr = s.post(url, data=payload, timeout=20)
        body = tr.text[:200]
        print("POST", short(url), "->", tr.status_code, "|", repr(body))
    except Exception as e:
        print("POST", short(url), "-> ERR", repr(e)[:80])

# Can the mobile API be reached with the mses COOKIE session alone (no Bearer)?
print("\n=== mobile API with mses cookie session (no Bearer) ===")
mobile_headers = {
    "User-Agent": "Talenta/13740 CFNetwork/3860.100.1 Darwin/25.0.0",
    "x-app-version": "2.126.0",
    "x-device-model": "iPhone14,2",
    "x-os-version": "iOS 18.7",
    "Accept": "*/*",
}
tests = [
    "https://api.mekari.com/internal/talenta-mobile/v1/dashboard/user",
    "https://api.mekari.com/internal/talenta-mobile/v1/attendance/companies/2767/attendance_schedules/active?latitude=-6.2&longitude=106.9&show_multiple=1",
]
for url in tests:
    try:
        tr = s.get(url, headers=mobile_headers, timeout=20)
        print("GET", short(url), "->", tr.status_code, "|", repr(tr.text[:140]))
    except Exception as e:
        print("GET", short(url), "-> ERR", repr(e)[:80])
