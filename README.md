# Talenta API - Python Implementation

Python version of the Mekari Talenta HR automation tool for clocking in and out. This eliminates the need to manually open the Talenta app to perform attendance actions.

## Features

- **Automatic Authentication**: Login with email/password to automatically fetch session cookies
- **Manual Cookie Support**: Fallback to manual cookie extraction from browser
- **Auto Location Detection**: Uses IP-based geolocation (with fallback to configured coordinates)
- **CLI Tool**: Simple command-line interface for manual clock in/out
- **Automated Scheduler**: Schedule automatic clock in/out for weekdays
- **CSRF Protection**: Automatically fetches and includes CSRF tokens
- **Coordinate Encoding**: Double-encoded coordinates (Base64 + ROT13) for security

## Requirements

### Native Python

- Python 3.7 or higher
- Internet connection
- Talenta/Mekari account

### Docker (Recommended)

- Docker 20.10 or higher
- Docker Compose 1.29 or higher
- Talenta/Mekari account

## Installation

### Option 1: Docker (Recommended)

Docker provides the easiest way to run the application with all dependencies included.

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

### Option 2: Native Python

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
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

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
```

### Getting Cookies Manually (Method 2)

If automatic authentication fails, you can extract cookies manually:

1. Login to [Talenta](https://account.mekari.com/users/sign_in?app_referer=Talenta)
2. Open browser DevTools (F12)
3. Go to Application tab � Cookies � `https://hr.talenta.co`
4. Find `PHPSESSID` or `_identity` cookie
5. Copy the value to `config_local.py`

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
make up

# View logs (live)
make logs

# Manual clock in
make clockin

# Manual clock out
make clockout

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
    talenta_api.py          # Core API module
    execute.py              # CLI executor
    scheduler.py            # Automated scheduler
    location.py             # Location detection
    lib/
        __init__.py
        auth_helpers.py     # Authentication helpers
    config.py               # Configuration template
    config_local.py         # Your local config (not in git)
    requirements.txt        # Python dependencies
    setup.sh                # Setup script
    .gitignore              # Git ignore file
    README.md               # This file
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
| Package Manager    | npm            | pip                  |
| Configuration      | `config.js`    | `config.py`          |
| Session Management | Manual         | `requests.Session()` |

## Troubleshooting

### Import Errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Or install from pyproject.toml
pip install -e .
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
