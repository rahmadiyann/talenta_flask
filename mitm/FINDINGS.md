# Talenta mobile API — temuan reverse-engineering

Catatan dari sesi MITM (capture traffic app Talenta iOS v2.126.0). Dipakai buat
nulis ulang `src/api/talenta.py` ke API mobile baru setelah Mekari migrasi ke
`launchpad.mekari.com` (web lama `hr.talenta.co` mati).

## Status

| Bagian | Status |
|---|---|
| Endpoint API mobile | ✅ teridentifikasi |
| Endpoint schedule | ✅ confirmed (shape response jelas) |
| Endpoint clock in/out | ⏳ belum (nunggu capture pagi/sore) |
| **Cara dapat access token** | ❌ **BLOCKER** — lihat bawah |

## Base + auth

- Host API: **`https://api.mekari.com/internal/talenta-mobile/v1/...`**
- Auth: header **`Authorization: Bearer <access_token>`** (WAJIB; cookie `mses`
  aja ditolak `401 "The access token is missing"`).
- Token format: **`<sso_id>_<suffix>`** (69–76 char), contoh prefix
  `864ac7aa-4673-44b9-b019-2023ffa3ffbf_…`. `sso_id` = field di `dashboard/user`.
- Token **short-lived / di-revoke saat logout** (token sesi lalu udah 401 ~1 jam
  kemudian setelah user logout).
- Header lain yang dikirim app:
  - `User-Agent: Talenta/13740 CFNetwork/3860.100.1 Darwin/25.0.0`
  - `x-device-id`, `x-app-version: 2.126.0`, `x-device-model: iPhone14,2`, `x-os-version`

## Identitas (akun rahmadiyan)

Dari `GET /internal/talenta-mobile/v1/dashboard/user`:
- `id` (organisation_user_id) = `3939862`
- `company_id` = `2767`
- `sso_id` = `864ac7aa-4673-44b9-b019-2023ffa3ffbf`
- `email`, `id_employee=RM250480`, dst.

## Endpoint yang sudah kelihatan

- `GET .../attendance/companies/{company_id}/attendance_schedules/active?latitude=&longitude=&show_multiple=1`
  → shift HARI INI. Response:
  ```json
  {"status":200,"data":[{"current_shift_date":"2026-11-25","current_shift_name":"WFA",
    "current_shift_sc_in":"09:00:00","current_shift_sc_out":"18:00:00",
    "is_check_in":false,"actual_check_in":"00:00:00",
    "is_check_out":false,"actual_check_out":"00:00:00", ...}]}
  ```
  → `is_check_in`/`is_check_out` + `actual_check_in/out` = status clock hari ini (realtime!).
  → `current_shift_name` = WFA/WFO/dll.
- `GET .../attendance/timezone?latitude=&longitude=`
- `GET .../dashboard/user`  (identitas)
- `POST .../logout`  (revoke token — JANGAN dipanggil di automation)
- Lain: `/toggle`, `/subordinates`, `/dashboard/*`, `/time-sheet/setting/self`,
  `/inbox-notification`, `talenta-geolocation/v1/companies/{c}/users/{u}/live-tracking-status`

⚠️ **Belum ketemu**: endpoint schedule BULANAN (navigasi bulan di app ternyata
nggak ngehit endpoint baru di capture — mungkin ke-cache). Dan endpoint
**clock-in / clock-out** (user belum clock pas capture).

## BLOCKER: cara dapat access token

Flow login = **OAuth2 Authorization Code + PKCE**:
- `GET account.mekari.com/auth?client_id=QOA8dzKDsDAO3a08&response_type=code&scope=sso:profile&redirect_uri=https://api.mekari.com/mobile-platform-oauth2-redirection&code_challenge=<s256>&code_challenge_method=s256`
- login (account.mekari.com/users/sign_in) → redirect `sm.mekari.com/?ec=` → `account.mekari.com/auth` → `api.mekari.com/mobile-platform-oauth2-redirection?code=<CODE>`

**Token-nya nggak pernah muncul di HTTP:**
- `mobile-platform-oauth2-redirection?code=` balik **200 content-length 0** (kosong).
- **Nggak ada** request yang bawa `code_verifier`/`grant_type` (token exchange).
- `oauth/token` di account.mekari.com = 404, di api.mekari.com = 403 (WAF).
- Nggak ada `.well-known/openid-configuration`.
- Replikasi flow server-side: dapet `code` + cookie `mses`, TAPI nggak dapet token.

→ Kesimpulan: token dikirim ke app lewat **callback custom-URL-scheme iOS**
(ASWebAuthenticationSession) yang **nggak lewat jaringan HTTP** → invisible ke MITM.
Jadi **belum bisa mint token murni server-side** kayak dulu (dulu dari cookie
`_session_token`, sekarang udah nggak ada).

## Yang perlu di-capture berikutnya (sesi pagi & sore)

1. **Clock-in** (pagi): URL, method, headers (Authorization), **body payload**
   (koordinat? encoding? csrf?), response.
2. **Clock-out** (sore): sama.
3. **Cek masa berlaku token**: kalau token sesi pagi MASIH valid pas sore (tanpa
   logout), berarti token long-lived → opsi "paste token manual tiap beberapa
   hari" jadi realistis.
4. Kalau bisa: sekali **fresh login tanpa logout** sambil ngawasin apakah ada
   token endpoint tersembunyi.

## Opsi solusi (buat didiskusiin)

- **A. Android capture** — di Android, callback OAuth sering lewat Chrome Custom
  Tabs yang BISA di-MITM, atau token endpoint-nya visible. Paling mungkin buat
  nge-crack token acquisition. Butuh device/emulator Android + apk-mitm/Frida
  (kalau pinning).
- **B. Semi-auto** — kalau token ternyata long-lived (cek sore nanti): tambah
  field "paste mobile token" per akun, user refresh manual tiap N hari.
- **C. Terus gali token endpoint** — kemungkinan kecil kalau emang custom-scheme.
