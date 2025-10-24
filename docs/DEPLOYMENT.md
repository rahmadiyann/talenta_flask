# Deployment Guide

This guide covers deploying Talenta API to various platforms.

## Table of Contents

- [Docker Hub](#docker-hub)
- [Railway](#railway)
- [Render](#render)
- [Heroku](#heroku)

---

## Docker Hub

Push your image to Docker Hub for easy deployment on any platform.

### Prerequisites

- Docker installed locally
- Docker Hub account (create at [hub.docker.com](https://hub.docker.com))

### Steps

```bash
# 1. Login to Docker Hub
docker login

# 2. Build the image with your username
docker build -t yourusername/talenta-api:latest .

# 3. (Optional) Test the image locally
docker run -e EMAIL="your.email@company.com" \
           -e PASSWORD="yourpassword" \
           -e TZ="Asia/Jakarta" \
           -p 5000:5000 \
           yourusername/talenta-api:latest

# 4. Push to Docker Hub
docker push yourusername/talenta-api:latest
```

### Multi-platform Build (ARM + x86)

For deployment on ARM platforms (e.g., Apple Silicon, Raspberry Pi):

```bash
# Enable buildx
docker buildx create --use

# Build and push for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 \
  -t yourusername/talenta-api:latest \
  --push .
```

---

## Railway

Railway is the easiest platform for deployment with automatic HTTPS and environment management.

### Method 1: From GitHub (Recommended)

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/talenta-api.git
   git push -u origin master
   ```

2. **Deploy on Railway**
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect the Dockerfile

3. **Configure Environment Variables**

   In Railway dashboard, go to Variables tab and add:
   ```
   EMAIL=your.email@company.com
   PASSWORD=yourpassword
   LATITUDE=-6.000
   LONGITUDE=107.000
   TIME_CLOCK_IN=09:00
   TIME_CLOCK_OUT=17:00
   TZ=Asia/Jakarta

   # Optional
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
   TELEGRAM_CHAT_ID=123456789
   ```

4. **Deploy**
   - Click "Deploy"
   - Railway automatically builds and deploys
   - View logs in real-time

### Method 2: From Docker Hub

1. **Push to Docker Hub first** (see Docker Hub section above)

2. **Create Railway Project**
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy Docker Image"
   - Enter: `yourusername/talenta-api:latest`

3. **Configure Variables** (same as Method 1)

4. **Deploy**

### Method 3: Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project (in project directory)
railway init

# Set environment variables
railway variables set EMAIL="your.email@company.com"
railway variables set PASSWORD="yourpassword"
railway variables set LATITUDE="-6.000"
railway variables set LONGITUDE="107.000"
railway variables set TIME_CLOCK_IN="09:00"
railway variables set TIME_CLOCK_OUT="17:00"
railway variables set TZ="Asia/Jakarta"

# Deploy
railway up

# View logs
railway logs
```

### Railway Configuration

The project includes `railway.json` with optimal settings:
- Uses Dockerfile for build
- Restart on failure (max 10 retries)
- Runs scheduler by default

### Railway Notes

- **Port**: Automatically set via `$PORT` environment variable (no configuration needed)
- **Cost**: $5/month free credit (hobby plan)
- **Logs**: View in dashboard or via `railway logs`
- **Domain**: Free `.up.railway.app` subdomain with HTTPS
- **Uptime**: 24/7 service
- **Restart**: Automatic restart on crashes

---

## Render

Render is another great option with a free tier.

### Steps

1. **Push to Docker Hub** (see Docker Hub section)

2. **Create Web Service on Render**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Select "Deploy an existing image from a registry"
   - Enter: `yourusername/talenta-api:latest`

3. **Configure Service**
   - Name: `talenta-api`
   - Region: Choose closest to your location
   - Instance Type: Free (or paid for better performance)

4. **Add Environment Variables**
   ```
   EMAIL=your.email@company.com
   PASSWORD=yourpassword
   LATITUDE=-6.000
   LONGITUDE=107.000
   TIME_CLOCK_IN=09:00
   TIME_CLOCK_OUT=17:00
   TZ=Asia/Jakarta
   ```

5. **Deploy**
   - Click "Create Web Service"
   - Render will pull and deploy your image

### Render Notes

- **Port**: Automatically set via `$PORT` environment variable
- **Free Tier**: Available with limitations (sleeps after 15 min inactivity)
- **Logs**: View in dashboard
- **Domain**: Free `.onrender.com` subdomain with HTTPS

---

## Heroku

Heroku is a classic PaaS with container support.

### Prerequisites

- Heroku account
- Heroku CLI installed

### Steps

```bash
# 1. Login to Heroku
heroku login

# 2. Create app
heroku create your-talenta-api

# 3. Login to Heroku Container Registry
heroku container:login

# 4. Build and push the image
heroku container:push web -a your-talenta-api

# 5. Release the image
heroku container:release web -a your-talenta-api

# 6. Set environment variables
heroku config:set EMAIL="your.email@company.com" -a your-talenta-api
heroku config:set PASSWORD="yourpassword" -a your-talenta-api
heroku config:set LATITUDE="-6.000" -a your-talenta-api
heroku config:set LONGITUDE="107.000" -a your-talenta-api
heroku config:set TIME_CLOCK_IN="09:00" -a your-talenta-api
heroku config:set TIME_CLOCK_OUT="17:00" -a your-talenta-api
heroku config:set TZ="Asia/Jakarta" -a your-talenta-api

# 7. View logs
heroku logs --tail -a your-talenta-api
```

### Heroku Notes

- **Port**: Automatically set via `$PORT` environment variable
- **Cost**: Free tier discontinued, starts at $7/month
- **Logs**: Use `heroku logs --tail`
- **Domain**: Free `.herokuapp.com` subdomain with HTTPS

---

## Environment Variables Reference

Required variables for all platforms:

| Variable | Description | Example |
|----------|-------------|---------|
| `EMAIL` | Talenta login email | `user@company.com` |
| `PASSWORD` | Talenta password | `yourpassword` |
| `LATITUDE` | Location latitude | `-6.000` |
| `LONGITUDE` | Location longitude | `107.000` |
| `TIME_CLOCK_IN` | Clock in time | `09:00` |
| `TIME_CLOCK_OUT` | Clock out time | `17:00` |
| `TZ` | Timezone | `Asia/Jakarta` |

Optional variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | `123456789:ABC...` |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | `123456789` |
| `PORT` | Server port (auto-set by platforms) | `5000` |
| `COOKIES_TALENTA` | Manual cookies (fallback) | `PHPSESSID=...` |

---

## Monitoring

### View Logs

**Railway:**
```bash
railway logs
```

**Render:**
- View in dashboard

**Heroku:**
```bash
heroku logs --tail -a your-app-name
```

### API Endpoints

Check if your deployment is running:

```bash
# Health check
curl https://your-app-url.com/health

# Automation status
curl https://your-app-url.com/status

# Disable automation
curl -X POST https://your-app-url.com/disable

# Enable automation
curl -X POST https://your-app-url.com/enable
```

---

## Troubleshooting

### Container Not Starting

1. Check logs for errors
2. Verify all required environment variables are set
3. Ensure email/password are correct
4. Check if Talenta login page structure changed

### Port Binding Issues

- The app automatically reads `$PORT` from environment
- No need to set `PORT` manually on Railway/Render/Heroku
- For local testing, set `PORT=5000` explicitly if needed

### Authentication Failed

- Verify credentials are correct
- Try manual cookie authentication as fallback
- Check if 2FA is enabled on Talenta (not supported)

### Jobs Not Running

- Check timezone setting (`TZ` environment variable)
- Verify time format is `HH:MM` (e.g., `09:00`, not `9:00`)
- Check logs for schedule confirmation messages
- Jobs only run Monday-Friday

---

## Cost Comparison

| Platform | Free Tier | Paid (Starter) | Notes |
|----------|-----------|----------------|-------|
| Railway | $5 credit/month | $5 usage-based | Best DX, auto-sleep disabled |
| Render | ✅ (with sleep) | $7/month | Sleeps after 15 min inactivity |
| Heroku | ❌ | $7/month | No free tier anymore |

**Recommendation**: Start with Railway for the best experience.

---

## Security Best Practices

1. **Never commit** `.env` or `config_local.py` files
2. **Use environment variables** for all sensitive data
3. **Rotate credentials** regularly
4. **Enable HTTPS only** (automatic on all platforms)
5. **Monitor logs** for suspicious activity
6. **Add authentication** to API endpoints if exposed publicly

---

## Next Steps

After deployment:

1. ✅ Test health endpoint: `https://your-app.com/health`
2. ✅ Check logs to verify scheduler is running
3. ✅ Test manual clock in/out if needed
4. ✅ Set up monitoring/alerts
5. ✅ Configure Telegram notifications

---

**Happy Deploying!** 🚀

For issues or questions, check the main [README.md](README.md) or open an issue on GitHub.
