#!/bin/sh
set -eu
python manage.py migrate --noinput
if [ "${SEED_DEMO:-0}" = "1" ]; then
  python manage.py seed_demo
fi
python manage.py bootstrap_admin
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --access-logfile -
