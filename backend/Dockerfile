# BotForge backend — deployable image for Hugging Face Spaces / Railway / Render.
#
# Port handling: Hugging Face Spaces expects the app on 7860 (and injects no PORT);
# Railway/Render inject $PORT. `${PORT:-7860}` in the CMD covers both.
FROM python:3.11-slim

# System deps: build-essential for packages with native wheels; libgomp1 for
# torch/onnxruntime used by sentence-transformers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Keep Python output unbuffered so logs stream to the host, and don't write .pyc.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Cache the embedding model inside the image dir so it survives across requests.
    HF_HOME=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers

# Install Python deps first (layer cached unless requirements.txt changes).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model at build time so the first request isn't slow
# and the container works even if outbound HF access is restricted at runtime.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the application code.
COPY . .

# Vectors (embedded Chroma) live here. On hosts without a persistent volume this
# resets on redeploy — fine for a demo; mount a volume here for real persistence.
RUN mkdir -p /app/chroma_data

EXPOSE 7860

# Shell form so ${PORT:-7860} is expanded by the shell at runtime.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}
