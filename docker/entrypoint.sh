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

# run migrations (safe to run every start)
flask db upgrade

# run DB initializer to insert default rows
python init_db.py

# Set up cron job for invoice reminders (every day at 6 AM)
echo "Setting up cron job for invoice reminders..."
# Use the same python executable the container will use so cron runs the
# environment that has installed packages (avoid system/python path mismatch).
PYTHON_BIN=$(command -v python || command -v python3 || true)
if [ -z "$PYTHON_BIN" ]; then
    PYTHON_BIN=/usr/bin/python
fi
echo "0 6 * * * cd /myapp && $PYTHON_BIN /myapp/send_reminders.py >> /var/log/invoice_reminders.log 2>&1" | crontab -

# Start cron daemon in background with error handling
echo "Starting cron daemon..."
if command -v crond &> /dev/null; then
    crond -f &
    CRON_PID=$!
    echo "Cron daemon started with PID $CRON_PID"
elif command -v cron &> /dev/null; then
    service cron start
    echo "Cron service started"
else
    echo "Warning: Neither crond nor cron service found. Invoice reminders will not run automatically."
    echo "Please ensure the container has a cron service installed."
fi

# start app
exec python app.py
