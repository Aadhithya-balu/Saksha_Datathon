#!/bin/sh

echo "======================================"
echo "Starting Saksha Application..."
echo "======================================"

mkdir -p /app/uploads

echo "Starting FastAPI..."

uvicorn app.main:app --host 0.0.0.0 --port 8000 &

echo "Starting Nginx..."

exec nginx -g "daemon off;"