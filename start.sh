#!/bin/sh

echo "======================================"
echo "Starting Saksha Application..."
echo "======================================"

mkdir -p /app/uploads

APP_PORT="${PORT:-80}"
echo "Listening on port ${APP_PORT}"

if [ -n "$PORT" ]; then
  sed -i "s/listen 80;/listen ${APP_PORT};/" /etc/nginx/conf.d/default.conf
fi

echo "Starting FastAPI..."

uvicorn app.main:app --host 0.0.0.0 --port 8000 &

echo "Starting Nginx..."

exec nginx -g "daemon off;"