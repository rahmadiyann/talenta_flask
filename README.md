# Talenta API - Python Implementation

Python version of the Mekari Talenta HR automation tool for clocking in and out. This eliminates the need to manually open the Talenta app to perform attendance actions.

## Features

- **Automatic Authentication**: Login with email/password to automatically fetch session cookies
- **Manual Cookie Support**: Fallback to manual cookie extraction from browser
- **Auto Location Detection**: Uses IP-based geolocation (with fallback to configured coordinates)
- **CLI Tool**: Simple command-line interface for manual clock in/out
- **Automated Scheduler**: Schedule automatic clock in/out for weekdays
- **Attendance Duplicate Prevention**: Checks if you've already clocked in/out before posting to prevent duplicate attendance records
- **Web API Control**: REST API endpoints to enable/disable automation remotely via HTTP requests
- **CSRF Protection**: Automatically fetches and includes CSRF tokens
- **Coordinate Encoding**: Double-encoded coordinates (Base64 + ROT13) for security

## Requirements

### Native Python

- Python 3.9 or higher
- uv (fast Python package installer) - installed automatically by setup script
- Internet connection
- Talenta/Mekari account

### Docker (Recommended)

- Docker 20.10 or higher
- Docker Compose 1.29 or higher
- Talenta/Mekari account

## Why uv?

This project uses **uv** instead of pip for dependency management. Benefits include:

- **10-100x faster** than pip for dependency resolution and installation
- **Reproducible builds** with `requirements.lock` file
- **Smaller Docker images** with better layer caching
- **Modern Python packaging** using `pyproject.toml` standard
- **Drop-in replacement** for pip - same commands, better performance

Read more: [uv documentation](https://docs.astral.sh/uv/)

## Installation

### Option 1: Railway Deployment (Cloud)

Deploy to Railway with one click or via CLI:

**One-Click Deploy:**

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

**Via Railway CLI:**

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Initialize project (from this directory)
railway init

# Set environment variables
railway variables set EMAIL="your.email@company.com"
railway variables set PASSWORD="yourpassword"
railway variables set LATITUDE="-6.000"
railway variables set LONGITUDE="107.000"
railway variables set TIME_CLOCK_IN="09:00"
railway variables set TIME_CLOCK_OUT="17:00"
railway variables set TZ="Asia/Jakarta"

# Optional: Telegram notifications
railway variables set TELEGRAM_BOT_TOKEN="123456789:ABCdefGHI..."
railway variables set TELEGRAM_CHAT_ID="123456789"

# Deploy
railway up
```

**Important Railway Notes:**
- The PORT environment variable is automatically set by Railway (no need to configure)
- Railway provides free $5/month credit for hobby projects
- The scheduler will run 24/7 in the cloud
- View logs with: `railway logs`

### Option 2: Docker Hub + Railway/Other Platforms

Push your Docker image to Docker Hub for deployment on Railway, Render, or any platform:

**Step 1: Build and Push to Docker Hub**

```bash
# Build the image
docker build -t yourusername/talenta-api:latest .

# Login to Docker Hub
docker login

# Push to Docker Hub
docker push yourusername/talenta-api:latest
```

**Step 2: Deploy on Railway using Docker image**

1. Go to [Railway](https://railway.app)
2. Create new project → Deploy from Docker image
3. Enter: `yourusername/talenta-api:latest`
4. Add environment variables in Railway dashboard
5. Deploy!

### Option 3: Docker (Local)

Docker provides the easiest way to run the application locally with all dependencies included.

**Quick Start:**

```bash
# 1. Create configuration file
cp config.py config_local.py

# 2. Edit config_local.py with your credentials
nano config_local.py

# 3. Build and start the scheduler
make build
make up

# 4. View logs
make logs
```

See [Docker Usage](#docker-usage) section for more commands.

### Option 4: Native Python (Local Development)

### Quick Setup

Run the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

This will:

1. Create a virtual environment
2. Install dependencies
3. Create a `config_local.py` file

### Manual Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Create virtual environment with uv
uv venv venv --python 3.11

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies with uv
uv pip install -r pyproject.toml

# Copy configuration file
cp config.py config_local.py
```

## Configuration

Edit `config_local.py` and configure your settings:

```python
# Method 1: Automatic authentication (recommended)
EMAIL = 'your.email@company.com'
PASSWORD = 'yourpassword'

# Method 2: Manual cookie authentication (fallback)
COOKIES_TALENTA = 'PHPSESSID=<value>'

# Location fallback
LONGITUDE = '107.000'
LATITUDE = '-6.000'

# Scheduler times
TIME_CLOCK_IN = "09:00"
TIME_CLOCK_OUT = "17:00"

# Telegram notifications (optional)
TELEGRAM_BOT_TOKEN = '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'
TELEGRAM_CHAT_ID = '123456789'
```

### Getting Cookies Manually (Method 2)

If automatic authentication fails, you can extract cookies manually:

1. Login to [Talenta](https://account.mekari.com/users/sign_in?app_referer=Talenta)
2. Open browser DevTools (F12)
3. Go to Application tab � Cookies � `https://hr.talenta.co`
4. Find `PHPSESSID` or `_identity` cookie
5. Copy the value to `config_local.py`

### Telegram Notifications (Optional)

Telegram notifications alert you when attendance is skipped due to manual clock in/out that you've already performed. This helps you stay informed about the automation's behavior.

**Step 1 - Create Bot:**

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts to name your bot
4. Copy the bot token provided (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

**Step 2 - Get Chat ID:**

1. Start a conversation with your new bot (click the link provided by BotFather)
2. Send any message to your bot (e.g., "Hello")
3. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in your browser (replace `<YOUR_BOT_TOKEN>` with your actual token)
4. Find the `"chat":{"id":` field in the JSON response
5. Copy the numeric chat ID (e.g., `123456789`)

**Step 3 - Configure:**

Add to `.env` file or `config_local.py`:

```python
TELEGRAM_BOT_TOKEN = '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'
TELEGRAM_CHAT_ID = '123456789'
```

**Testing:**

Notifications will be sent when the automation detects you've already clocked in/out manually.

**Note:**

This is optional - the automation works without Telegram, you just won't receive notifications.

### Web API Control

The scheduler includes a built-in web server for remote control of the automation.

**Overview:**

The web server starts automatically with the scheduler on port 5000, providing REST API endpoints for controlling automation behavior.

**Endpoints:**

- **`POST /disable`** - Disable automation (scheduled jobs won't execute)

  Example:

  ```bash
  curl -X POST http://localhost:5000/disable
  ```

  Response:

  ```json
  {
  	"success": true,
  	"message": "Automation disabled successfully",
  	"state": { "enabled": false }
  }
  ```

- **`POST /enable`** - Enable automation (resume scheduled jobs)

  Example:

  ```bash
  curl -X POST http://localhost:5000/enable
  ```

  Response:

  ```json
  {
  	"success": true,
  	"message": "Automation enabled successfully",
  	"state": { "enabled": true }
  }
  ```

- **`GET /status`** - Check current automation state

  Example:

  ```bash
  curl http://localhost:5000/status
  ```

  Response:

  ```json
  {
  	"success": true,
  	"state": { "enabled": true },
  	"message": "Automation is currently enabled"
  }
  ```

- **`GET /health`** - Health check endpoint

  Example:

  ```bash
  curl http://localhost:5000/health
  ```

  Response:

  ```json
  {
  	"status": "healthy"
  }
  ```

- **`POST /clockin`** - Trigger manual clock in

  Example:

  ```bash
  curl -X POST http://localhost:5000/clockin
  ```

  Response:

  ```json
  {
  	"success": true,
  	"message": "Clock in successful",
  	"result": { "status": 200, "message": "Success" }
  }
  ```

- **`POST /clockout`** - Trigger manual clock out

  Example:

  ```bash
  curl -X POST http://localhost:5000/clockout
  ```

  Response:

  ```json
  {
  	"success": true,
  	"message": "Clock out successful",
  	"result": { "status": 200, "message": "Success" }
  }
  ```

**Use Cases:**

- Temporarily disable automation when on vacation
- Manually trigger clock in/out via API without running the CLI
- Integrate with home automation systems
- Control via mobile apps or scripts
- Remote management from anywhere
- Trigger attendance from external systems or workflows

**Docker Access:**

When running in Docker, the API is accessible at `http://localhost:5000` (port is mapped in docker-compose.yml).

**State Persistence:**

The automation state is stored in-memory and resets to "enabled" on container restart.

**Security Note:**

The API has no authentication - it's designed for local/trusted network use. For production, consider adding authentication or running behind a reverse proxy with auth.

## Usage

### Docker Usage

#### Using Makefile (Easiest)

The Makefile provides convenient commands for all operations:

```bash
# View all available commands
make help

# Build the Docker image
make build

# Start the scheduler (runs in background)
# This also starts the web API on port 5000
make up

# View logs (live)
make logs

# Manual clock in (via Docker)
make clockin

# Manual clock out (via Docker)
make clockout

# Manual clock in (via API)
make api-clockin

# Manual clock out (via API)
make api-clockout

# Stop the scheduler
make down

# Restart the scheduler
make restart

# Check container status
make status

# Open shell in container
make shell

# View configuration
make config

# Clean everything (containers, images, volumes)
make clean

# Railway deployment commands
make railway-health      # Check Railway deployment health
make railway-status      # Check automation status
make railway-clockin     # Trigger clock in on Railway
make railway-clockout    # Trigger clock out on Railway
make railway-enable      # Enable automation on Railway
make railway-disable     # Disable automation on Railway
```

#### Using Docker Compose Directly

```bash
# Start scheduler in background
docker-compose up -d

# View logs
docker-compose logs -f

# Manual clock in
docker-compose run --rm talenta-clockin

# Manual clock out
docker-compose run --rm talenta-clockout

# Stop scheduler
docker-compose down
```

#### Using Docker Directly

```bash
# Build image
docker build -t talenta-api:latest .

# Run scheduler
docker run -d \
  --name talenta-scheduler \
  -v $(pwd)/config_local.py:/app/config_local.py:ro \
  talenta-api:latest scheduler

# Manual clock in
docker run --rm \
  -v $(pwd)/config_local.py:/app/config_local.py:ro \
  talenta-api:latest clockin

# View logs
docker logs -f talenta-scheduler

# Stop
docker stop talenta-scheduler
docker rm talenta-scheduler
```

#### Configuration via Environment Variables

Instead of `config_local.py`, you can use environment variables:

Create a `.env` file:

```bash
EMAIL=your.email@company.com
PASSWORD=yourpassword
LATITUDE=-6.000
LONGITUDE=107.000
TIME_CLOCK_IN=09:00
TIME_CLOCK_OUT=17:00
TZ=Asia/Jakarta
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

Then start with:

```bash
docker-compose --env-file .env up -d
```

### Native Python Usage

#### Activate Virtual Environment

Always activate the virtual environment before running:

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Manual Clock In/Out

**Clock In:**

```bash
python execute.py clockin
```

**Clock Out:**

```bash
python execute.py clockout
```

#### Automated Scheduler

Run the scheduler to automatically clock in/out at configured times:

```bash
python scheduler.py
```

The scheduler will:

- Run Monday-Friday only
- Clock in at `TIME_CLOCK_IN`
- Clock out at `TIME_CLOCK_OUT`
- Keep running until stopped with Ctrl+C

### Using as a Service

For production use, run the scheduler as a background service:

#### Using systemd (Linux)

Create `/etc/systemd/system/talenta-scheduler.service`:

```ini
[Unit]
Description=Talenta Clock In/Out Scheduler
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/talenta_flask
ExecStart=/path/to/talenta_flask/venv/bin/python scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl enable talenta-scheduler
sudo systemctl start talenta-scheduler
sudo systemctl status talenta-scheduler
```

#### Using screen (Linux/Mac)

```bash
screen -S talenta
python scheduler.py
# Press Ctrl+A then D to detach
# Reattach with: screen -r talenta
```

## Project Structure

```
talenta_flask/
├── src/
│   ├── api/
│   │   ├── talenta.py          # Core Talenta API functions
│   │   └── server.py           # Flask web server for control API
│   ├── cli/
│   │   ├── execute.py          # Manual clock in/out CLI
│   │   └── scheduler.py        # Automated scheduler with web server
│   ├── config/
│   │   └── config_local.py     # Configuration (from env vars)
│   └── core/
│       ├── auth.py             # Authentication helpers
│       ├── location.py         # Location detection
│       ├── logger.py           # Logging setup
│       └── telegram.py         # Telegram notifications
├── scripts/
│   ├── entrypoint.sh           # Docker entrypoint
│   └── setup.sh                # Setup script
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker Compose configuration
├── Makefile                    # Convenient Docker commands
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## How It Works

### Authentication Flow

1. **Automatic Mode**: Uses email/password to simulate browser login

   - Fetches login page and extracts authenticity token
   - Submits login form
   - Gets authorization code
   - Follows SSO callback to get final session cookies

2. **Manual Mode**: Uses pre-extracted cookie from browser

### Location Detection

1. Attempts IP-based geolocation via `ip-api.com`
2. Falls back to configured coordinates if detection fails

### Attendance Posting

1. Fetches CSRF token from live-attendance page
2. Encodes coordinates (Base64 � ROT13)
3. Builds form data with encoded coordinates and status
4. Posts to Talenta API with all required headers
5. Returns success/failure response

### Duplicate Prevention

1. Before posting attendance, queries Talenta API for today's status
2. Checks if `final_check_in` or `final_check_out` already exists
3. If duplicate detected, skips posting and sends Telegram notification
4. Prevents double attendance records from manual + automated clock in/out

### Web API Control

1. Flask server runs in a daemon thread alongside the scheduler
2. Exposes REST endpoints on port 5000 for remote control
3. Scheduler checks automation state before executing each job
4. State is stored in-memory (resets to enabled on restart)
5. No authentication required (designed for local/trusted network use)

## API Reference

### talenta_api.py

**Functions:**

- `clock_in(lat, long, cookies, desc)` - Clock in to Talenta
- `clock_out(lat, long, cookies, desc)` - Clock out from Talenta
- `fetch_cookies(email, password)` - Automatically fetch session cookies

**Example:**

```python
import talenta_api

# Automatic authentication
cookies = talenta_api.fetch_cookies('email@example.com', 'password')

# Clock in
result = talenta_api.clock_in(
    lat='-6.000',
    long='107.000',
    cookies=cookies,
    desc='Hello I am In'
)
print(result)
```

### location.py

**Functions:**

- `detect_location()` - Auto-detect location via IP
- `get_location(config)` - Get location with fallback

**Example:**

```python
import location

# Auto-detect with fallback
loc = location.get_location({
    'latitude': '-6.000',
    'longitude': '107.000'
})
print(loc)  # {'latitude': '...', 'longitude': '...'}
```

## Differences from Node.js Version

| Feature            | Node.js        | Python               |
| ------------------ | -------------- | -------------------- |
| HTTP Library       | Native `fetch` | `requests`           |
| Encoding           | Manual ROT13   | `codecs.encode()`    |
| Scheduling         | `node-cron`    | `schedule`           |
| Process Management | PM2            | systemd/screen       |
| Package Manager    | npm/pnpm       | uv (formerly pip)    |
| Configuration      | `config.js`    | `config.py`          |
| Session Management | Manual         | `requests.Session()` |
| Dependency Lock    | package-lock   | requirements.lock    |

## Troubleshooting

### Import Errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies with uv
uv pip install -r pyproject.toml

# Or sync dependencies (recommended)
uv pip sync pyproject.toml

# For development dependencies
uv pip install -r pyproject.toml --extra dev
```

### Authentication Failed

- Verify email and password are correct
- Try manual cookie extraction
- Check if Mekari login page structure changed

### Location Detection Failed

- Check internet connectivity
- Verify fallback coordinates in config
- Use manual coordinates for reliability

### Scheduler Not Running

- Ensure `TIME_CLOCK_IN` and `TIME_CLOCK_OUT` are set
- Check that script has execution permissions
- Run manually first to test: `python scheduler.py`

### 403 Signature Error

- CSRF token may be invalid
- Cookie may have expired
- Try automatic authentication to get fresh cookies

### Telegram Notifications Not Working

- Verify bot token and chat ID are correct
- Test by sending a message to your bot first
- Check logs for Telegram-related errors
- Ensure the bot token format is correct (should contain a colon)
- Visit the getUpdates URL to verify your chat ID

### Web API Not Accessible

- Verify the scheduler is running (`make status` or `docker ps`)
- Check that port 5000 is not blocked by firewall
- For Docker: ensure port mapping is correct in docker-compose.yml (5000:5000)
- Test with: `curl http://localhost:5000/health`
- Check logs for Flask startup messages

## Security Considerations

- **Never commit** `config_local.py` or `.env` files
- **Credentials** are stored locally only
- **HTTPS only** - all API calls use secure connections
- **CSRF protected** - tokens fetched and validated
- **Coordinates encoded** - Base64 + ROT13 encoding

## Contributing

See the main repository for contribution guidelines.

## License

ISC License - See LICENSE file in main repository

## Related

- **Node.js Version**: See parent directory for original JavaScript implementation
- **Flow Documentation**: See `FLOW.md` in parent directory for detailed architecture

## Support

For issues or questions, please open an issue on the GitHub repository.

---

**Note**: This tool is for personal use to automate legitimate attendance tracking. Use responsibly and in accordance with your company's policies.
