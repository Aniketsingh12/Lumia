# BotForge — Production Deployment

## Architecture

- **Frontend**: Vercel (React + Vite)
- **Backend**: Railway (FastAPI + Celery)
- **Database**: Supabase (PostgreSQL + Auth + Storage)
- **Vector DB**: ChromaDB (self-hosted on Railway)
- **Cache/Queue**: Redis (Railway add-on)

## Deploy Frontend (Vercel)

```bash
cd frontend
vercel --prod
```

Set environment variables in Vercel dashboard:
- `VITE_API_URL` = your Railway backend URL
- `VITE_SUPABASE_URL` = your Supabase URL
- `VITE_SUPABASE_ANON_KEY` = your Supabase anon key

## Deploy Backend (Railway)

```bash
cd backend
railway up
```

Set environment variables in Railway:
- All variables from `.env.example`
- `REDIS_URL` = Railway Redis add-on URL

## Deploy Widget

Build and serve `widget/dist/widget.js` from your backend or CDN.

```bash
cd widget
npm run build
# Upload dist/widget.js to your CDN or serve from backend
```

## Domain Setup

1. Point `botforge.app` to Vercel
2. Point `api.botforge.app` to Railway
3. Update CORS in `backend/app/main.py`
