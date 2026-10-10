#!/bin/sh
# Azure App Service startup command: sh startup.sh
exec gunicorn config.wsgi \
  --bind=0.0.0.0:${PORT:-8000} \
  --workers=2 \
  --threads=4 \
  --timeout=120 \
  --access-logfile=-
