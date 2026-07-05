# build frontend
FROM node:20-bookworm-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# backend + built static
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY --from=frontend /fe/dist ./static
RUN uv pip install --system .
EXPOSE 5120
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5120"]