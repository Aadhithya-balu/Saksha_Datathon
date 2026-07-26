# ==========================================
# Stage 1 : Build React Frontend
# ==========================================
FROM node:20 AS frontend-build

WORKDIR /frontend

COPY datathon/package*.json ./

RUN npm install

COPY datathon/ .

RUN npm run build


# ==========================================
# Stage 2 : Python + Nginx
# ==========================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install nginx
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx && \
    rm -f /etc/nginx/sites-enabled/default && \
    rm -f /etc/nginx/sites-available/default && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ==========================================
# Backend
# ==========================================

COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# ==========================================
# Frontend
# ==========================================

COPY --from=frontend-build /frontend/dist /usr/share/nginx/html

# ==========================================
# Nginx Configuration
# ==========================================

COPY nginx.conf /etc/nginx/conf.d/default.conf

# ==========================================
# Startup Script
# ==========================================

COPY start.sh /start.sh

RUN chmod +x /start.sh

EXPOSE 80

CMD ["/start.sh"]