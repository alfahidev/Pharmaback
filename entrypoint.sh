#!/bin/sh
set -e

echo "=== Starting PharmaBack Production Container ==="

# Wait for PostgreSQL Database connection if DB_HOST is configured
if [ -n "$DB_HOST" ]; then
    echo "Checking PostgreSQL connection at $DB_HOST:${DB_PORT:-5432}..."
    python - << 'EOF'
import sys, time, os
import psycopg

host = os.getenv("DB_HOST", "localhost")
port = int(os.getenv("DB_PORT", "5432"))
user = os.getenv("DB_USER", "pharma_user")
password = os.getenv("DB_PASSWORD", "pharma_pass")
dbname = os.getenv("DB_NAME", "pharmaback")

max_retries = 30
for attempt in range(1, max_retries + 1):
    try:
        conn = psycopg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=3,
        )
        conn.close()
        print(f"✅ PostgreSQL database '{dbname}' is ready and accessible!")
        sys.exit(0)
    except Exception as e:
        print(f"⏳ Waiting for PostgreSQL ({attempt}/{max_retries})... ({e})")
        time.sleep(2)

print("❌ ERROR: Could not connect to PostgreSQL within timeout period.")
sys.exit(1)
EOF
fi

# Collect static assets
echo "Collecting static assets..."
python manage.py collectstatic --noinput

# Apply database migrations
echo "Applying database migrations (Row-Level Security & Multi-tenancy)..."
python manage.py migrate --noinput

# Configure Gunicorn runtime parameters for 4 vCPU VPS
GUNICORN_WORKERS=${GUNICORN_WORKERS:-3}
GUNICORN_THREADS=${GUNICORN_THREADS:-4}
GUNICORN_MAX_REQUESTS=${GUNICORN_MAX_REQUESTS:-2000}
GUNICORN_MAX_REQUESTS_JITTER=${GUNICORN_MAX_REQUESTS_JITTER:-200}
PORT=${PORT:-8000}
TIMEOUT=${GUNICORN_TIMEOUT:-60}

echo "🚀 Starting Gunicorn server on 0.0.0.0:$PORT ($GUNICORN_WORKERS workers x $GUNICORN_THREADS threads, recycling every $GUNICORN_MAX_REQUESTS reqs)..."
exec gunicorn core.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --worker-class gthread \
    --workers "$GUNICORN_WORKERS" \
    --threads "$GUNICORN_THREADS" \
    --max-requests "$GUNICORN_MAX_REQUESTS" \
    --max-requests-jitter "$GUNICORN_MAX_REQUESTS_JITTER" \
    --worker-tmp-dir /dev/shm \
    --keep-alive 5 \
    --timeout "$TIMEOUT" \
    --access-logfile - \
    --error-logfile -