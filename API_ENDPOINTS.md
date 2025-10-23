# API Endpoints Reference

Complete reference for all available API endpoints in Talenta API.

## Base URL

- **Local Docker**: `http://localhost:5000`
- **Railway Deployment**: `https://talentaflask-production.up.railway.app`

---

## Endpoints

### 1. Health Check

Check if the API server is running.

**Endpoint**: `GET /health`

**Request**:
```bash
curl http://localhost:5000/health
```

**Response**:
```json
{
  "status": "healthy"
}
```

---

### 2. Check Automation Status

Get the current automation state (enabled/disabled).

**Endpoint**: `GET /status`

**Request**:
```bash
curl http://localhost:5000/status
```

**Response**:
```json
{
  "success": true,
  "state": {
    "enabled": true
  },
  "message": "Automation is currently enabled"
}
```

---

### 3. Enable Automation

Enable scheduled jobs to execute.

**Endpoint**: `POST /enable`

**Request**:
```bash
curl -X POST http://localhost:5000/enable
```

**Response**:
```json
{
  "success": true,
  "message": "Automation enabled successfully",
  "state": {
    "enabled": true
  }
}
```

---

### 4. Disable Automation

Disable scheduled jobs from executing.

**Endpoint**: `POST /disable`

**Request**:
```bash
curl -X POST http://localhost:5000/disable
```

**Response**:
```json
{
  "success": true,
  "message": "Automation disabled successfully",
  "state": {
    "enabled": false
  }
}
```

---

### 5. Manual Clock In

Trigger manual clock in via API.

**Endpoint**: `POST /clockin`

**Request**:
```bash
curl -X POST http://localhost:5000/clockin
```

**Response (Success)**:
```json
{
  "success": true,
  "message": "Clock in successful",
  "result": {
    "status": 200,
    "message": "Success",
    "data": {
      "attendance_id": "12345",
      "timestamp": "2025-01-20 09:00:00"
    }
  }
}
```

**Response (Error)**:
```json
{
  "success": false,
  "error": "Authentication failed: Invalid credentials",
  "message": "Clock in failed"
}
```

**Notes**:
- Uses credentials from environment variables
- Automatically fetches authentication cookies
- Falls back to manual cookies if auto-auth fails
- Returns detailed Talenta API response in `result` field

---

### 6. Manual Clock Out

Trigger manual clock out via API.

**Endpoint**: `POST /clockout`

**Request**:
```bash
curl -X POST http://localhost:5000/clockout
```

**Response (Success)**:
```json
{
  "success": true,
  "message": "Clock out successful",
  "result": {
    "status": 200,
    "message": "Success",
    "data": {
      "attendance_id": "12345",
      "timestamp": "2025-01-20 18:00:00"
    }
  }
}
```

**Response (Error)**:
```json
{
  "success": false,
  "error": "Already clocked out today",
  "message": "Clock out failed"
}
```

**Notes**:
- Uses credentials from environment variables
- Automatically fetches authentication cookies
- Falls back to manual cookies if auto-auth fails
- Returns detailed Talenta API response in `result` field

---

## Makefile Commands

### Local Docker Commands

```bash
# API control
make api-enable        # Enable automation
make api-disable       # Disable automation
make api-status        # Check status
make api-health        # Health check
make api-clockin       # Trigger clock in
make api-clockout      # Trigger clock out

# Full test suite
make api-test          # Test all endpoints
```

### Railway Deployment Commands

```bash
# API control on Railway
make railway-enable      # Enable automation
make railway-disable     # Disable automation
make railway-status      # Check status
make railway-health      # Health check
make railway-clockin     # Trigger clock in
make railway-clockout    # Trigger clock out

# Full test suite (Railway)
make api-test            # Test all Railway endpoints
```

---

## Use Cases

### 1. Manual Attendance
Trigger clock in/out without running Docker containers locally:
```bash
curl -X POST https://your-deployment.railway.app/clockin
```

### 2. Vacation Mode
Disable automation when on vacation:
```bash
curl -X POST https://your-deployment.railway.app/disable
```

### 3. External Integration
Integrate with other systems (home automation, mobile apps):
```bash
# From iOS Shortcuts
curl -X POST https://your-deployment.railway.app/clockin

# From Home Assistant
service: rest_command.talenta_clockin
```

### 4. Workflow Automation
Trigger from CI/CD or scheduled tasks:
```bash
# GitHub Actions
- name: Clock In
  run: |
    curl -X POST ${{ secrets.TALENTA_API_URL }}/clockin
```

### 5. Monitoring
Check if automation is still enabled:
```bash
# Cron job
*/30 * * * * curl https://your-deployment.railway.app/health
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error description",
  "message": "User-friendly error message"
}
```

Common errors:
- `Authentication failed` - Invalid credentials
- `Already clocked in/out today` - Duplicate attendance
- `Configuration error` - Missing EMAIL/PASSWORD or COOKIES_TALENTA
- `Network error` - Unable to reach Talenta API

---

## Authentication

API endpoints use credentials from environment variables:

**Priority order:**
1. Try `EMAIL` + `PASSWORD` (automatic authentication)
2. Fall back to `COOKIES_TALENTA` (manual cookies)
3. Return error if both fail

**Configuration:**
```bash
# Set in Railway/Docker environment
EMAIL=your.email@company.com
PASSWORD=yourpassword

# Or use manual cookies
COOKIES_TALENTA=PHPSESSID=abc123...
```

---

## Security Notes

⚠️ **Important**:
- No authentication required for API endpoints
- Designed for trusted network use (local/VPN)
- For production: Add authentication or use reverse proxy
- Railway deployments are publicly accessible by default
- Consider using environment variables for API keys if needed

**Recommendations**:
- Deploy behind VPN or firewall
- Use Railway private networking if available
- Add basic auth via reverse proxy (nginx, Caddy)
- Monitor access logs regularly

---

## Testing

### Test All Endpoints (Local)
```bash
make api-test
```

### Test Individual Endpoints
```bash
# Health
curl http://localhost:5000/health

# Status
curl http://localhost:5000/status

# Enable
curl -X POST http://localhost:5000/enable

# Disable
curl -X POST http://localhost:5000/disable

# Clock in
curl -X POST http://localhost:5000/clockin

# Clock out
curl -X POST http://localhost:5000/clockout
```

### Test Railway Deployment
```bash
# Replace URL with your Railway deployment URL
curl https://talentaflask-production.up.railway.app/health
curl -X POST https://talentaflask-production.up.railway.app/clockin
```

---

## Response Times

Typical response times:

| Endpoint | Average | Notes |
|----------|---------|-------|
| `/health` | <10ms | Instant |
| `/status` | <10ms | Instant |
| `/enable` | <10ms | Instant |
| `/disable` | <10ms | Instant |
| `/clockin` | 2-5s | Includes auth + Talenta API call |
| `/clockout` | 2-5s | Includes auth + Talenta API call |

---

## Rate Limiting

No built-in rate limiting. Recommendations:

- Don't abuse Talenta API (respect their rate limits)
- Manual clock in/out: Max 2-3 times per day
- Status checks: Reasonable intervals (every 30+ minutes)
- Use scheduled jobs instead of manual triggers when possible

---

## Changelog

### v1.0.0 (Current)
- ✅ Added `/clockin` endpoint for manual clock in
- ✅ Added `/clockout` endpoint for manual clock out
- ✅ Improved error handling
- ✅ Added Railway deployment support
- ✅ Added Makefile commands for easy testing

---

## Support

- 📖 Main documentation: [README.md](README.md)
- 🚀 Deployment guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- 🐛 Issues: Create GitHub issue
- 💬 Questions: Check documentation first

---

**Last Updated**: January 2025
