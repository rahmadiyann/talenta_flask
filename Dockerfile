# Dockerfile for Talenta API Python
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for better caching
COPY pyproject.toml .

# Install Python dependencies with uv
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x scripts/entrypoint.sh src/cli/execute.py src/cli/scheduler.py

# Expose Flask web server port
EXPOSE 5000

# Set entrypoint
ENTRYPOINT ["./scripts/entrypoint.sh"]

# Default command (scheduler)
CMD ["scheduler"]
