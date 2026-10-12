FROM node:22-bookworm-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
COPY shared/layouts.json /build/shared/layouts.json
RUN npm run build

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_FRONTEND_DIR=/app/frontend/dist

COPY backend/pyproject.toml backend/uv.lock /app/backend/
RUN pip install --no-cache-dir uv && uv sync --project /app/backend --locked
COPY backend /app/backend
COPY --from=frontend-build /build/frontend/dist /app/frontend/dist

EXPOSE 8000
VOLUME ["/data"]
ENV APP_DATA_DIR=/data
WORKDIR /app/backend
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"]
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
