#!/usr/bin/env bash
# Start the Talenta/Mekari MITM capture proxy.
#
#   ./mitm/run.sh
#
# Then point the phone's Wi-Fi HTTP proxy at this machine's Tailscale IP, port
# 8080, and install + trust the mitmproxy CA (see mitm.md §5 and §13).
#
# Only mekari.com / talenta.co are decrypted; every other app is tunnelled blind.
set -euo pipefail

cd "$(dirname "$0")/.."   # project root
MITM_DIR="mitm"

export MITM_STATE_DIR="$PWD/$MITM_DIR/state"
mkdir -p "$MITM_STATE_DIR" "$MITM_DIR/.mitmproxy"

echo "📡 Talenta MITM proxy on 0.0.0.0:8080"
echo "   Phone proxy  -> $(tailscale ip -4 2>/dev/null | head -1 || echo '<this-host-IP>'):8080"
echo "   CA cert      -> $MITM_DIR/.mitmproxy/mitmproxy-ca-cert.pem (install on phone)"
echo "   Capture log  -> $MITM_DIR/state/capture.log   (tail -f to watch)"
echo "   Full capture -> $MITM_DIR/state/capture.jsonl (contains tokens!)"
echo ""

exec "$MITM_DIR/.venv/bin/mitmdump" \
  -s "$MITM_DIR/capture.py" \
  --listen-host 0.0.0.0 \
  --listen-port 8080 \
  --set "confdir=$PWD/$MITM_DIR/.mitmproxy" \
  --set block_global=false \
  --set 'allow_hosts=^(.*\.)?(mekari\.com|talenta\.co)(:\d+)?$' \
  --set flow_detail=0
