# Changelog - Configuration and Timezone Updates

## Changes Made

### 1. Updated `config_local.py` - Environment Variable Loading

**Changes:**

- Added `python-dotenv` import to load variables from `.env` file
- All configuration now reads from environment variables with sensible defaults
- Smart cookie formatting (auto-adds PHPSESSID prefix if needed)
- Added TIMEZONE configuration (defaults to Asia/Jakarta)

**Key Features:**

```python
from dotenv import load_dotenv
load_dotenv()

EMAIL = os.getenv('EMAIL', '')
PASSWORD = os.getenv('PASSWORD', '')
COOKIES_TALENTA = os.getenv('COOKIES_TALENTA', '')
LONGITUDE = os.getenv('LONGITUDE', '107.000')
LATITUDE = os.getenv('LATITUDE', '-6.000')
TIME_CLOCK_IN = os.getenv('TIME_CLOCK_IN', '09:00')
TIME_CLOCK_OUT = os.getenv('TIME_CLOCK_OUT', '17:00')
TIMEZONE = os.getenv('TZ', 'Asia/Jakarta')
```

### 2. Updated `scheduler.py` - Asia/Jakarta Timezone Support

**Changes:**

- Added timezone handling with multiple fallbacks:
  - Primary: `zoneinfo.ZoneInfo` (Python 3.9+, built-in)
  - Fallback 1: `pytz` (if available)
  - Fallback 2: Simple GMT+7 timezone
- System timezone is set to Asia/Jakarta on startup
- Current time and day displayed when scheduler starts
- Execution time shown for each clock in/out operation

**Key Features:**

```python
# Timezone display on startup
print(f"   Timezone: Asia/Jakarta (GMT+7)")
print(f"   Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"   Current day: {current_day}")

# Execution time shown for each job
current_time = datetime.now(TIMEZONE)
print(f'   Time: {current_time.strftime("%Y-%m-%d %H:%M:%S %Z")}')
```

### 3. Updated `requirements.txt`

**Added:**

- `pytz>=2023.3` - Timezone fallback for Python < 3.9

**Existing:**

- `python-dotenv>=1.0.0` - Already present for .env support

### 4. Updated `.env.example`

**Added:**

- `TZ=Asia/Jakarta` - Timezone configuration example

## Usage

### Method 1: Using .env file (Recommended)

1. Create `.env` file from example:

```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:

```bash
EMAIL=your.email@company.com
PASSWORD=yourpassword
LATITUDE=-6.000
LONGITUDE=107.000
TIME_CLOCK_IN=09:00
TIME_CLOCK_OUT=17:00
TZ=Asia/Jakarta
```

3. Run scheduler:

```bash
python scheduler.py
```

### Method 2: Using Docker (Easiest)

The `.env` file is automatically loaded by Docker Compose:

```bash
# Create and edit .env
cp .env.example .env
nano .env

# Build and run
make build
make up

# View logs (will show Asia/Jakarta timezone)
make logs
```

### Method 3: Direct environment variables

```bash
export EMAIL=your.email@company.com
export PASSWORD=yourpassword
export TZ=Asia/Jakarta
python scheduler.py
```

## Expected Output

### Scheduler Startup

```
🕐 Starting scheduler...
   Timezone: Asia/Jakarta (GMT+7)
   Current time: 2025-10-13 23:17:05 WIB
   Current day: Monday
   Clock in scheduled for:  09:00 (Mon-Fri)
   Clock out scheduled for: 17:00 (Mon-Fri)

📍 Using location: -6.175392, 106.827153 (Jakarta, Indonesia)
✅ Authentication configured successfully

✅ Scheduler started successfully!
   Press Ctrl+C to stop
```

### Clock In Execution

```
⏰ Executing scheduled clock in...
   Time: 2025-10-14 09:00:00 WIB
✅ Clock in successful!
{
  "status": "success",
  "message": "Clock in recorded"
}
```

### Clock Out Execution

```
⏰ Executing scheduled clock out...
   Time: 2025-10-14 17:00:00 WIB
✅ Clock out successful!
{
  "status": "success",
  "message": "Clock out recorded"
}
```

## Timezone Details

**Asia/Jakarta (WIB - Western Indonesian Time)**

- UTC Offset: **GMT+7** (no daylight saving)
- Fixed offset year-round
- Same as: Indochina Time (ICT), Thailand, Vietnam

**Supported Timezones:**
You can change `TZ` to any valid timezone:

- `Asia/Jakarta` (GMT+7)
- `Asia/Singapore` (GMT+8)
- `Asia/Manila` (GMT+8)
- `Asia/Bangkok` (GMT+7)
- `Asia/Ho_Chi_Minh` (GMT+7)
- etc.

## Backwards Compatibility

All changes are **backwards compatible**:

- Existing `config_local.py` files still work (will use hardcoded values)
- Works with Python 3.7+ (with pytz fallback for < 3.9)
- Works with Python 3.9+ (uses built-in zoneinfo)
- Docker environment already configured correctly

## Testing

### Test timezone detection

```bash
python -c "
from datetime import datetime
from zoneinfo import ZoneInfo

tz = ZoneInfo('Asia/Jakarta')
now = datetime.now(tz)
print(f'Current time: {now.strftime(\"%Y-%m-%d %H:%M:%S %Z\")}')
"
```

### Test configuration loading

```bash
python -c "
import config_local
print(f'Email: {config_local.EMAIL}')
print(f'Timezone: {config_local.TIMEZONE}')
print(f'Clock in: {config_local.TIME_CLOCK_IN}')
"
```

### Test scheduler (dry run)

```bash
# Set times to current time + 1 minute for quick test
export TIME_CLOCK_IN="23:18"
export TIME_CLOCK_OUT="23:19"
export TZ=Asia/Jakarta
python scheduler.py
```

## Troubleshooting

### Issue: Wrong timezone showing

**Solution:**

```bash
# Make sure TZ is set
export TZ=Asia/Jakarta

# Or in .env file
echo "TZ=Asia/Jakarta" >> .env

# Restart scheduler
```

### Issue: ImportError: No module named 'zoneinfo'

**Solution (Python < 3.9):**

```bash
# Install pytz fallback
pip install pytz

# Or reinstall all requirements
pip install -r requirements.txt
```

### Issue: Time is off by several hours

**Cause:** System timezone mismatch

**Solution:**

```bash
# Check current timezone
date +%Z

# For Docker, TZ env var is already set in docker-compose.yml
# For native Python, set TZ before running:
export TZ=Asia/Jakarta
python scheduler.py
```

## Docker Notes

The Docker setup automatically handles timezone:

- `TZ=Asia/Jakarta` is set in `docker-compose.yml`
- Container timezone is properly configured
- Scheduler will show WIB (Western Indonesian Time)
- No additional configuration needed

## Migration Guide

If you have an existing installation:

1. **Pull latest changes**
2. **Install new requirements:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Create .env file:**

   ```bash
   cp .env.example .env
   nano .env  # Add your credentials
   ```

4. **Test the scheduler:**

   ```bash
   python scheduler.py
   ```

5. **Verify timezone in output**

## Support

- Timezone issues: Check TZ environment variable
- Configuration issues: Verify .env file exists and is readable
- Import errors: Reinstall requirements
- Docker issues: Rebuild container with `make rebuild`
