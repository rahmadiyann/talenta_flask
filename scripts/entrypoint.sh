#!/bin/bash
# Entrypoint script for Talenta API Docker container

set -e

# Ensure the data directory for the SQLite database exists
mkdir -p "$(dirname "${DB_PATH:-data/talenta.db}")" 2>/dev/null || true

# Create config from environment variables if config_local.py doesn't exist
if [ ! -f "src/config/config_local.py" ]; then
    echo "Creating config from environment variables..."
    cat > src/config/config_local.py <<EOF
# Auto-generated configuration from environment variables

EMAIL = '${EMAIL:-}'
PASSWORD = '${PASSWORD:-}'
COOKIES_TALENTA = '${COOKIES_TALENTA:-PHPSESSID=<value>}'
LONGITUDE = '${LONGITUDE:-107.000}'
LATITUDE = '${LATITUDE:--6.000}'
TIME_CLOCK_IN = '${TIME_CLOCK_IN:-09:00}'
TIME_CLOCK_OUT = '${TIME_CLOCK_OUT:-17:00}'
TIMEZONE = '${TZ:-Asia/Jakarta}'
TELEGRAM_BOT_TOKEN = '${TELEGRAM_BOT_TOKEN:-}'
TELEGRAM_CHAT_ID = '${TELEGRAM_CHAT_ID:-}'
MEKARI_BEARER_TOKEN = '${MEKARI_BEARER_TOKEN:-}'
MEKARI_ORGANISATION_ID = '${MEKARI_ORGANISATION_ID:-}'
MEKARI_ORGANISATION_USER_ID = '${MEKARI_ORGANISATION_USER_ID:-}'
EOF
    echo "✅ Configuration created"
fi

# Parse command
case "$1" in
    scheduler)
        echo "🕐 Starting scheduler with Gunicorn WSGI server..."
        exec python3 -m src.cli.scheduler
        ;;
    clockin)
        echo "⏰ Clocking in..."
        exec python3 -m src.cli.execute clockin "${2:-}"
        ;;
    clockout)
        echo "⏰ Clocking out..."
        exec python3 -m src.cli.execute clockout "${2:-}"
        ;;
    bash|sh)
        echo "🐚 Starting shell..."
        exec /bin/bash
        ;;
    *)
        # If first argument looks like a Python script, run it
        if [[ "$1" == *.py ]]; then
            echo "🐍 Running Python script: $@"
            exec python3 "$@"
        else
            echo "Usage: $0 {scheduler|clockin|clockout|bash|<script.py>}"
            exit 1
        fi
        ;;
esac
