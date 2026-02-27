#!/usr/bin/env bash
set -e

DB_HOST=${POSTGRES_HOST:-aba_db}
DB_PORT=${POSTGRES_PORT:-5432}

echo "Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT"; do
  sleep 1
done
echo "Postgres is available."

# ensure FLASK_APP points to factory
export FLASK_APP=${FLASK_APP:-app:create_app}

# First run DB initializer to ensure base tables exist and default rows are present
# This makes sure `db.create_all()` runs before Alembic migrations that alter tables.
python init_db.py

# run migrations (safe to run every start)
flask db upgrade

# Set up cron job for invoice reminders based on settings
echo "Setting up cron job for invoice reminders..."
# Use the same python executable the container will use so cron runs the
# environment that has installed packages (avoid system/python path mismatch).
PYTHON_BIN=$(command -v python || command -v python3 || true)
if [ -z "$PYTHON_BIN" ]; then
    PYTHON_BIN=/usr/bin/python
fi
export PYTHON_BIN
python setup_cron_schedule.py

# Create log directory for cron jobs if it doesn't exist
mkdir -p /var/log
chmod 777 /var/log

# Start cron daemon in the background with process supervision
echo "Starting cron daemon..."
# Run cron in foreground mode instead of using service (which creates background process)
# This allows proper signal handling when container is shut down
/usr/sbin/cron -f &
CRON_PID=$!
echo "Cron daemon started with PID $CRON_PID"

# Trap signals to ensure cron is gracefully shut down
trap "kill $CRON_PID 2>/dev/null || true; exit 0" SIGTERM SIGINT

# Give cron a moment to initialize and read the crontab
sleep 2

# Start Flask app as the main process
# This will become PID 1, and signals will be properly forwarded
python app.py
