# MITM proxy di Ubuntu — panduan

Versi Linux dari [mitm-proxy-guide.md](mitm-proxy-guide.md). Konsepnya persis
sama; yang beda cuma perintah instalasi, cara jalanin, dan beberapa jebakan OS.

Panduan ini pakai Ubuntu 22.04 / 24.04, tapi berlaku umum buat Debian dan
distro lain dengan penyesuaian nama paket.

---

## 1. Kapan butuh ini

Butuh MITM proxy kalau:

- App-nya nggak punya API publik, tapi datanya kelihatan di layar.
- Protokolnya HTTPS dan lo perlu lihat isi request/response.
- Autentikasi dikunci tanda tangan per-request, jadi lo **nggak bisa** manggil
  sendiri — satu-satunya sumber data adalah trafik app itu.

Yang nggak bisa diselesaikan dengan cara ini:

- Push notification (APNs/FCM) — terenkripsi, nggak lewat proxy HTTP.
- App dengan certificate pinning keras.
- Data yang cuma muncul kalau app-nya dibuka (app ditutup = nggak ada trafik).

---

## 2. Arsitektur

```
HP ──Wi-Fi proxy──► mitmproxy (Ubuntu) ──► internet
                          │
                          └─ addon: filter + tulis ke file
```

mitmproxy bertindak sebagai HTTP proxy:

1. Client kirim `CONNECT host:443`.
2. Host **masuk daftar boleh** → mitmproxy bikin sertifikat palsu yang
   ditandatangani CA kita, buka TLS, isinya kebaca.
3. Host **nggak masuk** → tunnel buta, byte dioper apa adanya.

Poin 2–3 itu yang bikin setup ini aman dipakai di HP sehari-hari: makin sempit
daftar boleh, makin sedikit app yang rusak.

Prinsip yang sama berlaku di Windows; dokumen ini cuma beda permukaan.

---

## 3. Instalasi

### Paket sistem

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ca-certificates
```

`python3-venv` wajib — kalau nggak ada, `python3 -m venv` gagal dengan pesan
yang agak nyasar ("ensurepip is not available").

### Virtualenv khusus project

Jangan install mitmproxy ke Python sistem. Pakai venv di dalam folder project
biar versinya terkunci dan nggak bikin konflik:

```bash
cd ~/gojek-watch                 # folder project
python3 -m venv vendor/venv
vendor/venv/bin/pip install --upgrade pip
vendor/venv/bin/pip install --upgrade mitmproxy
vendor/venv/bin/mitmdump --version        # cek
```

### Folder kerja

```bash
mkdir -p state vendor/.mitmproxy
```

`state/` buat hasil capture, `vendor/.mitmproxy/` buat CA dan config mitmproxy.

---

## 4. Jalanin proxy

```bash
cd ~/gojek-watch

GOJEK_STATE_DIR="$PWD/state" \
vendor/venv/bin/mitmdump \
  -s scripts/mitm_capture.py \
  --listen-host 0.0.0.0 \
  --listen-port 8080 \
  --set "confdir=$PWD/vendor/.mitmproxy" \
  --set block_global=false \
  --set 'allow_hosts=^(.*\.)?(gojekapi\.com|gojek\.com|goto-products\.com|gopayapi\.com|gopay\.co\.id|gojek\.link|heartbeat\.gojek-proxy\.test)$' \
  --set flow_detail=0
```

| Flag | Kenapa |
|---|---|
| `--listen-host 0.0.0.0` | biar bisa diakses dari HP, bukan cuma `127.0.0.1` |
| `confdir` | CA + config disimpan di situ; bikin stabil antar-run |
| `block_global=false` | **wajib**; default-nya cuma nerima koneksi localhost |
| `allow_hosts` | cuma host yang cocok yang dibuka |
| `flow_detail=0` | jangan banjirin console |

### allow_hosts, bukan ignore_hosts

Ini kesalahan yang paling mahal:

- `ignore_hosts` = daftar blokir → semua yang nggak terdaftar ikut di-MITM.
  Tiap app baru bakal kena (TikTok nggak bisa buka komentar, app bank error),
  dan nambalinya nggak akan pernah selesai.
- `allow_hosts` = daftar boleh → semua yang nggak cocok di-tunnel buta.
  Default-nya aman.

Pola regex:

```
^(.*\.)?(domain-a\.com|domain-b\.co\.id)$
```

`(.*\.)?` biar subdomain ikut, `$` biar nggak nyangkut ke domain yang mirip.

### Jalanin di background

Cara kasar:

```bash
mkdir -p state
GOJEK_STATE_DIR="$PWD/state" nohup vendor/venv/bin/mitmdump \
  -s scripts/mitm_capture.py \
  --listen-host 0.0.0.0 --listen-port 8080 \
  --set "confdir=$PWD/vendor/.mitmproxy" \
  --set block_global=false \
  --set 'allow_hosts=^(.*\.)?(gojekapi\.com|gojek\.com)$' \
  --set flow_detail=0 \
  > state/proxy.out 2>&1 &
```

Lebih rapi dan tahan reboot: pakai systemd (bagian 7).

---

## 5. Pasang CA di iPhone

1. Set proxy dulu: **Settings → Wi-Fi → (i) → Configure Proxy → Manual** →
   Server = IP Ubuntu, Port = 8080.
2. Buka `http://mitm.it` di Safari **lewat proxy** → pilih iOS → install.
3. **Settings → General → VPN & Device Management** → install profile.
4. **Settings → General → About → Certificate Trust Settings** → nyalakan
   toggle mitmproxy. *(Langkah ini paling sering kelewat, dan gejalanya nggak
   jelas: semua HTTPS gagal tanpa alasan.)*

File CA-nya ada di `vendor/.mitmproxy/mitmproxy-ca-cert.pem`. iOS lebih seneng
kalau ekstensinya `.crt`:

```bash
cp vendor/.mitmproxy/mitmproxy-ca-cert.pem vendor/.mitmproxy/mitmproxy-ca.crt
python3 -m http.server 8090 --directory vendor/.mitmproxy   # buat transfer
```

### Android (catatan)

Android 7+ nggak percaya user CA untuk app dengan `targetSdk ≥ 24`, kecuali
app-nya nge-izinin. Untuk app kayak gitu perlu rooted/Frida.

---

## 6. Verifikasi

Tes paling cepat, nggak butuh HP:

```bash
# host di luar daftar -> HARUS 200 (tunnel buta)
curl -sS -x http://127.0.0.1:8080 -o /dev/null -w '%{http_code}\n' https://example.com/

# host target tanpa -k -> HARUS gagal cert error (berarti di-MITM)
curl -sS -x http://127.0.0.1:8080 -o /dev/null -w '%{http_code}\n' https://api.gojekapi.com/
#   curl: (60) SSL certificate problem: unable to get local issuer certificate

# host target dengan -k -> HARUS balas HTTP (isinya kebaca)
curl -sSk -x http://127.0.0.1:8080 -o /dev/null -w '%{http_code}\n' https://api.gojekapi.com/
#   404
```

Kalau dua-duanya 200 tanpa `-k`, berarti `allow_hosts` nggak kepasang.
Kalau dua-duanya cert error, ada host lain yang ikut kebuka.

Cek socket:

```bash
ss -lntp | grep 8080
ss -tn state established '( sport = :8080 )'
```

---

## 7. systemd (biar nyala sendiri)

`/etc/systemd/system/gojek-watch-proxy.service`:

```ini
[Unit]
Description=gojek-watch MITM proxy
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=gojek
WorkingDirectory=/home/gojek/gojek-watch
Environment=PORT=8080
Environment=GOJEK_STATE_DIR=/home/gojek/gojek-watch/state
ExecStart=/home/gojek/gojek-watch/vendor/venv/bin/mitmdump \
  -s /home/gojek/gojek-watch/scripts/mitm_capture.py \
  --listen-host 0.0.0.0 --listen-port 8080 \
  --set confdir=/home/gojek/gojek-watch/vendor/.mitmproxy \
  --set block_global=false \
  --set allow_hosts=^(.*\.)?(gojekapi\.com|gojek\.com|goto-products\.com)$
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> Di unit file, `\` buat lanjut baris **nggak** bekerja seperti di shell.
> Kalau mau aman, tulis `ExecStart` dalam satu baris panjang.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gojek-watch-proxy
systemctl status gojek-watch-proxy
journalctl -u gojek-watch-proxy -f
```

Buka port kalau ufw aktif:

```bash
sudo ufw allow 8080/tcp
sudo ufw status
```

---

## 8. Log & rotasi

| File | Isi |
|---|---|
| `state/capture.log` | satu baris per request pesanan, enak buat `tail -f` |
| `state/capture.jsonl` | header + body lengkap |
| `state/presence.json` | denyut nadi client terakhir |

```bash
tail -f state/capture.log
```

Rotasi tanpa stop proxy (addon buka file per penulisan):

```bash
: > state/capture.log
: > state/capture.jsonl
```

`capture.jsonl` berisi token — perlakukan seperti password.

---

## 9. Jebakan khusus Linux

| Gejala | Penyebab | Solusi |
|---|---|---|
| `bash: $'\r': command not found` | file dari Windows (CRLF) | `sed -i 's/\r$//' scripts/*.sh` |
| `ensurepip is not available` | `python3-venv` belum ada | `sudo apt install python3-venv` |
| HP nggak bisa nyambung | `block_global` masih true | tambahin `--set block_global=false` |
| HP timeout padahal proxy hidup | ufw nutup 8080 | `sudo ufw allow 8080/tcp` |
| `mitmdump: not found` | venv belum dibuat | bagian 3 |
| Service langsung mati | path di unit salah, atau user nggak punya akses folder | `journalctl -u gojek-watch-proxy -n 50` |
| Addon nggak nulis file | `state/` nggak ada atau nggak writable | `mkdir -p state && chmod u+w state` |
| `mitm.it` nggak kebuka | HP belum lewat proxy | set proxy dulu, baru buka |
| Redirect ke `https://` gagal | CA belum di-trust | Certificate Trust Settings di iOS |

Jebakan yang **sama** dengan Windows (domain `.local`, pinning, socket nyangkut,
body biner) ada di [mitm-proxy-guide.md §8](mitm-proxy-guide.md#8-jebakan-yang-sudah-kena-biar-nggak-ngulang).

---

## 10. Kalau widget tetap di Windows

Proxy di Ubuntu artinya `capture.jsonl` ada di Ubuntu, sementara supervisor
(Windows) baca dari `state/` lokal. Tiga pilihan:

| Cara | Plus / minus |
|---|---|
| `rsync` tiap 1–2 detik | paling gampang; ada jeda 1–2 detik |
| NFS/SMB, Windows mount jadi drive | nggak ada jeda, nambah dependency |
| Ubah supervisor baca via HTTP | paling rapi, perlu ubah kode |

Contoh tarik berkala dari sisi Ubuntu (kalau Windows yang narik, pakai `scp`):

```bash
while true; do
  rsync -az ~/gojek-watch/state/ windows:/c/Users/<user>/.../GoJek/state/
  sleep 2
done
```

Kalau nanti mau benar-benar tanpa Windows: panel `tkinter` jalan di Linux, yang
hilang cuma ikon taskbar-nya (itu Win32 API).

---

## 11. Keamanan

- **Jangan** jalankan proxy ini di host yang port-nya kebuka ke internet.
  MITM proxy yang terbuka = siapa pun bisa lewat situ.
- `vendor/.mitmproxy/mitmproxy-ca-cert.pem` + private key-nya sensitif: siapa
  pun yang punya bisa membuka HTTPS device yang percaya CA itu.
- `state/capture.jsonl` berisi token. Jangan di-commit, hapus rutin:

  ```bash
  sudo systemctl stop gojek-watch-proxy
  rm -f state/capture.jsonl state/capture.log state/presence.json
  ```

- Selesai pakai: hapus juga CA dari iPhone (Settings → General → VPN & Device
  Management).

---

## 12. Checklist

- [ ] `python3-venv` terpasang
- [ ] `vendor/venv/bin/mitmdump` ada dan bisa `--version`
- [ ] `state/` dan `vendor/.mitmproxy/` ada
- [ ] jalan dengan `block_global=false`
- [ ] port 8080 kebuka di ufw
- [ ] iPhone: proxy diset, `mitm.it` kebuka, Certificate Trust di-on-kan
- [ ] `curl` tanpa `-k` gagal ke host target, 200 ke host lain
- [ ] systemd `enable` (kalau mau nyala sendiri)
- [ ] `capture.jsonl` sudah dianggap file sensitif

---

## 13. Setup konkret Talenta (siap pakai, on-demand)

> **Ini tool sekali-pakai, bukan service.** Tujuannya cuma **nangkep endpoint +
> data** API mobile Talenta/Mekari yang baru (setelah mereka migrasi ke
> `launchpad.mekari.com`). Nyalakan pas butuh capture, matikan + bersihin setelah
> selesai. Nggak usah systemd / nggak usah nyala terus. Dipakai lagi nanti kalau
> endpoint Talenta berubah.

Semua udah disiapin di folder `mitm/`:

```
mitm/
├─ .venv/          # mitmproxy 12 (gitignored)
├─ .mitmproxy/     # CA + private key (gitignored) — jangan dibagi
├─ capture.py      # addon: filter mekari/talenta, tulis ke state/
├─ run.sh          # runner siap pakai
└─ state/          # capture.log + capture.jsonl (gitignored, berisi TOKEN)
```

Host yang di-MITM dibatasi ke `*.mekari.com` dan `*.talenta.co` saja — app lain
di HP (bank, WA, dll) di-tunnel buta, nggak kebuka.

### Langkah

1. **Jalanin proxy** (dari root project, foreground biar kelihatan live):

   ```bash
   ./mitm/run.sh
   ```

   Biarin jendela ini jalan. Di terminal lain: `tail -f mitm/state/capture.log`.

2. **Set proxy di iPhone** — pakai IP Tailscale laptop (HP udah di tailnet):

   - **Settings → Wi-Fi → (i) → Configure Proxy → Manual**
   - Server = **`100.105.114.42`**  ·  Port = **`8080`**

   > Pakai Tailscale IP, jadi nggak peduli HP & laptop beda Wi-Fi — asal Tailscale
   > nyala di HP. (WSL2 nggak langsung keliatan di LAN, makanya lewat Tailscale.)

3. **Pasang + trust CA mitmproxy di iPhone** (sekali aja):

   - Buka `http://mitm.it` di Safari **lewat proxy** → pilih **iOS** → install profile
   - **Settings → General → VPN & Device Management** → install
   - **Settings → General → About → Certificate Trust Settings** → nyalakan toggle
     mitmproxy *(wajib — kalau nggak, semua HTTPS gagal tanpa pesan jelas)*

   CA-nya juga ada di `mitm/.mitmproxy/mitmproxy-ca-cert.pem` kalau mau transfer manual.

4. **Simulasikan aktivitas di app Talenta** sambil proxy nyala:

   - Buka app → login (kalau diminta)
   - Buka **Live Attendance** → **Clock In**, lalu nanti **Clock Out**
   - Buka **Schedule / jadwal shift**
   - Tiap aksi bakal muncul di `capture.log`; yang penting ditandai **★**
     (url mengandung `attendance`/`clock`/`schedule`/`auth`/`token`).

5. **Stop proxy** (Ctrl+C di jendela run.sh) setelah semua ketangkep.

6. **Kasih hasilnya** — yang aku butuh dari `mitm/state/capture.jsonl` buat tiap
   aksi (bisa kasih full filenya, atau baris-baris ★):

   | Buat apa | Yang dibutuhin |
   |---|---|
   | Auth / token | request login + response yang ngasih `access_token`/Bearer |
   | Clock in/out | **URL**, **method**, **headers** (`Authorization`), **body payload**, response |
   | Schedule/shift | **URL** + query params, headers, bentuk response |
   | Host API baru | domain-nya apa sekarang (mis. `api.mekari.com/v2/...` yang baru) |

   Dari situ aku tulis ulang `src/api/talenta.py` biar pakai API mobile yang baru.

### Kalau app-nya gagal konek / cert error (pinning)

Kalau pas proxy nyala app Talenta **nggak bisa login / loading terus**, kemungkinan
**certificate pinning**. iOS susah di-bypass (butuh jailbreak). Opsi:

- Coba **Android** (device/emulator) + `apk-mitm` atau Frida/objection buat bypass pin.
- Atau cek dulu: tanpa pinning, request bakal nongol di `capture.log`. Kalau
  `capture.log` kosong total padahal app dipakai → kemungkinan besar pinning.

### Bersih-bersih setelah selesai (PENTING)

```bash
# hapus token hasil capture
rm -f mitm/state/capture.jsonl mitm/state/capture.log
```

- **Lepas proxy di iPhone**: Settings → Wi-Fi → (i) → Configure Proxy → **Off**.
- **(Opsional) hapus CA** dari iPhone kalau nggak dipakai lagi: Settings → General
  → VPN & Device Management → hapus profile mitmproxy.
- `capture.jsonl` berisi token — udah di-gitignore, tapi tetep hapus manual.