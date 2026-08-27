# Lumio — single-service image: React dashboard + FastAPI API in one container.
#
# Build context is the REPO ROOT (not backend/), because this needs both
# frontend/ and backend/. On Railway that means the service's Root Directory
# must be empty, not "backend".
#
# Why one service instead of two: one domain and one bill, and the dashboard
# ends up same-origin with the API, so the browser never makes a cross-origin
# call for it at all.

# ---- stage 1: build the dashboard ---------------------------------------
FROM node:20-alpine AS frontend
WORKDIR /fe

# Vite inlines VITE_* variables into the bundle at BUILD time, not runtime.
# Supplying VITE_API_URL only as a runtime variable would silently ship a bundle
# still pointing at the localhost fallback in src/lib/api.ts. Railway passes
# service variables into the build, so it arrives here as this ARG.
#
# For this single-service setup it should be the service's own public URL
# (frontend and API share an origin).
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Optional demo account for the login page's one-click "Explore the live demo"
# button. Same build-time constraint as VITE_API_URL above: these must be ARGs,
# not just runtime variables, or Vite would bake in empty strings and the button
# would never render. Unset on a real client deploy to hide the button entirely.
ARG VITE_DEMO_EMAIL
ENV VITE_DEMO_EMAIL=$VITE_DEMO_EMAIL
ARG VITE_DEMO_PASSWORD
ENV VITE_DEMO_PASSWORD=$VITE_DEMO_PASSWORD

# Dependencies first so this layer caches unless the lockfile changes.
# devDependencies are needed: `npm run build` runs `tsc` before `vite build`.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- stage 2: the API, plus the built dashboard --------------------------
FROM python:3.11-slim

# build-essential for packages with native wheels; libgomp1 for the
# torch/onnxruntime stack behind sentence-transformers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the embedding model into the image so the first upload doesn't pay for
# downloading it, and so the container works even where outbound access to
# huggingface.co is restricted at runtime.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY backend/ .

# app/main.py looks for the dashboard here and serves it (with an SPA fallback)
# when present; when absent it runs API-only, which is what local dev and the
# test suite do.
COPY --from=frontend /fe/dist ./static_frontend

# Embedded ChromaDB writes here. Mount a Railway volume at this path for the
# knowledge base to survive redeploys. chmod because some hosts run the
# container as a non-root user at runtime while every step above ran as root —
# without it the first document upload fails on a permission error.
RUN mkdir -p /app/chroma_data && chmod -R 777 /app/chroma_data

EXPOSE 8000

# Shell form so ${PORT} is expanded at runtime by the shell.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
