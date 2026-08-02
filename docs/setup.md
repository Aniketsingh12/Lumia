# BotForge — Local Development Setup

## Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (optional — only for async document ingestion)
- Supabase account (free tier)

## Quick Start (Windows)

Double-click `start.bat` from the repo root. It creates a Python venv,
installs deps, and launches the backend + frontend in two new windows.

## Manual Setup

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

### 3. Widget

```bash
cd widget
npm install
npm run build  # Generates dist/widget.js
```

### 4. Redis + Celery

```bash
# Start Redis
redis-server

# Start Celery worker (in backend/)
celery -A app.tasks.celery_app worker --loglevel=info

# Start Celery beat (for periodic tasks)
celery -A app.tasks.celery_app beat --loglevel=info
```

### 5. Database

1. Create a Supabase project at https://supabase.com
2. Run the migration SQL: `python scripts/migrate.py`
3. Copy the SQL output into Supabase SQL Editor and execute

### 6. Seed Demo Data

```bash
python scripts/seed_demo.py
```

## Environment Variables

See `backend/.env.example` for all required variables.

Key ones:
- `SUPABASE_URL` / `SUPABASE_KEY` — from Supabase dashboard
- `CLAUDE_API_KEY` — from Anthropic (or use `LLM_PROVIDER=ollama` for free local LLM)
- `REDIS_URL` — default `redis://localhost:6379/0`
