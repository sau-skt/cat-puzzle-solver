FROM node:20-alpine AS webbuild

WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=webbuild /web/dist /app/static

RUN chmod +x docker-entrypoint.sh \
    && mkdir -p /app/storage

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
