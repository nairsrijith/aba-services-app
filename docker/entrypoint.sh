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

# start app
exec python app.py