# Dockerfile for Talenta API Python
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x entrypoint.sh execute.py scheduler.py

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# Default command (scheduler)
CMD ["scheduler"]
