# Dockerfile for Talenta API Python
# Uses uv for fast package installation
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Install system dependencies and uv
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with uv (much faster than pip)
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x entrypoint.sh execute.py scheduler.py

# Create volume mount point for config
VOLUME ["/app/config"]

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# Default command (scheduler)
CMD ["scheduler"]
