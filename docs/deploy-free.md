# Free Deployment Guide

Total cost: **$0/month** (plus LLM API usage, usually <$5/mo on cheap models).

## What you'll set up

1. **Supabase** — database + auth (free 500 MB)
2. **Upstash** — Redis (free 10k commands/day)
3. **Render** — Python backend + Celery worker (free, sleeps when idle)
4. **Vercel** — React frontend (free, always on)
5. **Groq** OR **Gemini** OR **Claude Haiku** — LLM

Total time: **~30 minutes**.

---

## 1. Push code to GitHub

```powershell
cd E:\botforge
git init
git add .
git commit -m "Initial commit"
gh repo create botforge --public --source=. --push
```

Don't have `gh`? Create the repo on github.com → copy the `git remote add` commands it gives you.

---

## 2. Supabase (database + auth)

1. Sign up at https://supabase.com (free, GitHub login works).
2. **New project** → name it `botforge` → strong DB password → pick region near you → **Create**.
3. Wait ~2 min for provisioning.
4. **Settings → API** — copy these three values:
   - `Project URL` → `SUPABASE_URL`
   - `anon public key` → `SUPABASE_KEY`
   - `service_role secret` → `SUPABASE_SERVICE_KEY`
5. **SQL Editor** → run the contents of `scripts/migrate.py`'s SQL (or paste your schema).

---

## 3. Upstash (Redis)

1. Sign up at https://upstash.com (free, GitHub login).
2. **Create Database** → name `botforge-redis` → pick region → **Free** tier → Create.
3. Copy the **`UPSTASH_REDIS_URL`** (starts with `rediss://`) → this is your `REDIS_URL`.

---

## 4. Pick an LLM provider (free options)

### Option A — Groq (fastest, free, recommended)
1. https://console.groq.com → sign up → API Keys → Create
2. Set `LLM_PROVIDER=openai` and point `OPENAI_API_KEY` at Groq's key, `OPENAI_BASE_URL=https://api.groq.com/openai/v1`, `OPENAI_MODEL=llama-3.3-70b-versatile`
3. Free tier: 30 req/min, plenty for demo

### Option B — Google Gemini (free)
1. https://aistudio.google.com → Get API Key
2. Free tier: 15 req/min on Gemini 1.5 Flash
3. (Needs minor adapter — see Option C if your code doesn't support Gemini yet)

### Option C — Claude Haiku (cheapest paid, ~$0.25 per million tokens)
1. https://console.anthropic.com → API Keys
2. Set `CLAUDE_API_KEY` and `CLAUDE_MODEL=claude-haiku-4-5-20251001`
3. $5 free credit on signup typically covers a portfolio demo for months

---

## 5. Deploy backend to Render

1. Sign up at https://render.com (GitHub login).
2. **New +** → **Blueprint** → connect your `botforge` repo.
3. Render reads `render.yaml` and creates **two services**: `botforge-api` (web) + `botforge-celery` (worker).
4. In the env-vars section, paste:
   - `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY` (from step 2)
   - `REDIS_URL` (from step 3)
   - `CLAUDE_API_KEY` (or whichever LLM you picked)
   - `APP_URL` → leave blank for now, fill after step 6
5. Click **Apply**. First deploy takes ~5 min.
6. Copy the live URL — looks like `https://botforge-api.onrender.com`.

**Free-tier caveat:** the service sleeps after 15 min idle. First request after sleep takes ~30s. Fine for a portfolio.

---

## 6. Deploy frontend to Vercel

1. Sign up at https://vercel.com (GitHub login).
2. **Add New → Project** → import the `botforge` repo.
3. **Root Directory** → `frontend` → it auto-detects Vite.
4. **Environment Variables**:
   - `VITE_API_URL` = your Render URL from step 5
5. **Deploy**. Takes ~2 min.
6. Copy the Vercel URL — looks like `https://botforge.vercel.app`.

---

## 7. Wire frontend URL back to backend

1. Render dashboard → `botforge-api` → **Environment** → set `APP_URL` to your Vercel URL.
2. The service auto-redeploys. Done.

---

## 8. Verify

- Open your Vercel URL → sign up → upload a doc → chat.
- API docs live at `https://botforge-api.onrender.com/docs`.

---

## Sharing with clients

Your live URLs:
- **App:** `https://botforge.vercel.app`
- **API:** `https://botforge-api.onrender.com`

Want a custom domain? Buy from Cloudflare (~$10/yr), point CNAME at Vercel — both Vercel and Render support custom domains on free tier.

---

## Keeping the free backend awake (optional)

Render free sleeps after 15 min. To keep it warm during demo hours:
- https://uptimerobot.com (free) → ping `/health` every 5 min
- Or use GitHub Actions: cron workflow hitting your `/health` endpoint

Don't ping 24/7 — Render free tier caps at 750 hrs/month (≈ enough for one always-on service, but two services + pings = over).

---

## Going paid later

When you have paying clients:
- Render **Starter** ($7/mo) — no sleep, dedicated CPU
- Supabase **Pro** ($25/mo) — 8 GB DB, daily backups
- Custom domain on Cloudflare ($10/yr)

Total ~$32/mo for a real production setup. But $0 is fine until then.
