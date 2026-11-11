#!/usr/bin/env sh
set -eu

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_WAIT_TIMEOUT_SECONDS="${DB_WAIT_TIMEOUT_SECONDS:-60}"

if [ "${WAIT_FOR_DB:-true}" = "true" ]; then
  case "$DB_WAIT_TIMEOUT_SECONDS" in
    ''|*[!0-9]*) echo "DB_WAIT_TIMEOUT_SECONDS must be a positive integer." >&2; exit 1 ;;
  esac
  elapsed=0
  echo "Waiting for PostgreSQL..."
  while ! nc -z "$DB_HOST" "$DB_PORT"; do
    if [ "$elapsed" -ge "$DB_WAIT_TIMEOUT_SECONDS" ]; then
      echo "PostgreSQL did not become available within the configured timeout." >&2
      exit 1
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
fi

# Explicit commands allow an approved migrate operation without starting the web server.
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Applying approved migrations..."
  python manage.py migrate --noinput
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application --config deploy/gunicorn.conf.py
