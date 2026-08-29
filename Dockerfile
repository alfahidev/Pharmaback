# Production Dockerfile for PharmaBack Multi-Tenant SaaS Backend
# Base image: Official Python 3.12 Slim (Debian Bookworm)

FROM python:3.12-slim

# Set environment variables for Python runtime optimization & Home directory
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser \
    PORT=8000

WORKDIR /app

# Install minimal system dependencies (curl for container health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create a secure non-root user with a real home directory (avoids /nonexistent permission errors)
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --home /home/appuser --shell /bin/bash appuser

# Copy application source code
COPY . .

# Copy and set execution permissions on entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create required runtime directories and set proper ownership
RUN mkdir -p /home/appuser /app/staticfiles /app/media /app/logs && \
    chown -R appuser:appgroup /home/appuser /app /entrypoint.sh

# Switch to non-root user
USER appuser

# Expose Gunicorn application port
EXPOSE 8000

# Docker Healthcheck (probing local health endpoint)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/api/health/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
