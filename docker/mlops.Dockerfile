FROM python:3.12-slim

WORKDIR /app

COPY backend /app/backend
COPY mlflow /app/mlflow
COPY monitoring /app/monitoring

ENV PYTHONPATH=/app/backend

CMD ["python", "-m", "app.mlops"]
