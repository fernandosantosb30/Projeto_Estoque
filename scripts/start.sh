#!/usr/bin/env bash
set -euo pipefail
# Disco do Render só está montado no runtime; não acessar fotos no build/pre-deploy.
python manage.py check --deploy --fail-level WARNING
python manage.py migrate --noinput
python manage.py createcachetable
python manage.py setup_roles
python manage.py bootstrap_demo_admin
python manage.py collectstatic --noinput
python manage.py production_ready
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}" --workers "${WEB_CONCURRENCY:-2}" --threads "${GUNICORN_THREADS:-2}" --timeout 60 --access-logfile - --error-logfile -
