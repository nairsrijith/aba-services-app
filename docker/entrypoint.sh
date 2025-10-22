#!/usr/bin/env bash
set -e

DB_HOST=${POSTGRES_HOST:-db}
DB_PORT=${POSTGRES_PORT:-5432}

# wait for postgres
echo "Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; do
  sleep 1
done
echo "Postgres is available."

# run migrations
flask db upgrade

# start the app (change to gunicorn config you prefer)
exec gunicorn -b 0.0.0.0:8080 "app:app"