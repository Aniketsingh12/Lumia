# Deploying Lumio

Two paths, depending on what you need:

- **[Path A — Free portfolio deploy](#path-a--free-portfolio-deploy)** ($0/mo, sleeps when idle) — for a demo link recruiters and prospective clients can click.
- **[Path B — Production deploy](#path-b--production-deploy)** (~$5-7/mo, always on) — for a real client whose customers depend on it. Render and Railway are both set up in this repo.

Both use the same code. The difference is entirely environment variables.

---

## Before you deploy anything

Two things are mandatory regardless of path:

1. **Generate a real `JWT_SECRET`.** The value in `.env.example` is public — leaving it means anyone can forge a login token for any account.
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
2. **Never commit `backend/.env`.** It's already in `.gitignore` — keep it that way. Set secrets in your host's dashboard instead.

---

## Path A — Free portfolio deploy

| Piece | Service | Cost |
|---|---|---|
| LLM | **Together AI** — open-source models via an OpenAI-compatible API | Pay-per-token |
| Backend | **Hugging Face Spaces** (Docker, 16 GB RAM) | Free |
| Frontend | **Vercel** | Free |
| Database | in-memory dev DB (`USE_DEV_DB=true`) | Free |
| Vectors | embedded ChromaDB | Free |

### 1. Get a Together AI API key

Create a key at <https://api.together.ai>. Together serves the same open-source Llama models you can run locally with Ollama, but on their hardware — replies land in about a second instead of ~20s on a laptop CPU.

Because Together exposes an OpenAI-compatible API, this needs no code changes: the `openai` provider is simply pointed at their base URL.

### 2. Deploy the backend to Hugging Face Spaces

The backend already has a `Dockerfile`.

1. Create a Space at <https://huggingface.co/new-space> → **SDK: Docker** → **Blank**.
2. Push the **contents of `backend/`** to the Space repo, and add this `README.md` at its root (the `app_port` must match the Dockerfile's `7860`):

   ```markdown
   ---
   title: Lumio API
   emoji: ✨
   colorFrom: purple
   colorTo: blue
   sdk: docker
   app_port: 7860
   ---
   ```

3. In **Settings → Variables and secrets**, add:

   | Key | Value |
   |---|---|
   | `LLM_PROVIDER` | `openai` |
   | `OPENAI_BASE_URL` | `https://api.together.xyz/v1` |
   | `OPENAI_API_KEY` | your Together AI key — add as a **secret** |
   | `OPENAI_MODEL` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |
   | `USE_DEV_DB` | `true` |
   | `CHROMA_MODE` | `embedded` |
   | `JWT_SECRET` | the value you generated above — add as a **secret** |
   | `APP_URL` | your Vercel URL from step 3 |
   | `API_URL` | your Space URL, e.g. `https://you-lumio.hf.space` |

4. The Space builds (slow the first time — it installs torch and bakes in the embedding model). Verify: opening `https://<your-space>.hf.space/` returns `{"name":"Lumio API",...}`.

### 3. Deploy the frontend to Vercel

1. Import the repo at <https://vercel.com/new>.
2. **Root Directory:** `frontend` · **Framework:** Vite · Build `npm run build` · Output `dist`.
3. Environment variable:

   | Key | Value |
   |---|---|
   | `VITE_API_URL` | your Space URL — no trailing slash, no `/api` |

4. Deploy, then set `APP_URL` on the Space to this Vercel URL (that's what CORS and the widget embed use).

### 4. Log in

Use a seed account (in-memory dev DB): `admin@botforge.dev` / `admin123`.

### Free-tier caveats — know these before demoing

- **The backend sleeps after ~48h idle** and takes ~30s to wake. Open the demo link once before showing it to someone.
- **Data resets** whenever the Space rebuilds or wakes cold, because `USE_DEV_DB=true`. Seed logins always come back; bots and uploaded documents don't. Set `USE_DEV_DB=false` + Supabase to keep them.
- **Together AI bills per token** — cheap for a demo (a 70B model runs well under a cent per conversation), but it is not free like a sleeping container is. Keep an eye on usage if you make the demo public.

---

## Path B — Production deploy

Use this once a real client depends on it. Free tiers sleep, rate-limit, and offer no uptime guarantee — that's fine for a portfolio, not for someone's customers.

### 1. Database — Supabase

1. Create a project at <https://supabase.com>.
2. Run `scripts/migrate.py`, or paste the SQL schema from `docs/architecture.md` into the SQL editor.
3. Copy the project URL, anon key, and service-role key.
4. Set `USE_DEV_DB=false`.

### 2. Backend — Render *or* Railway

Both work and both are configured in this repo. Pick one:

| | **Render** (`render.yaml`) | **Railway** (`railway.toml`) |
|---|---|---|
| What deploys | API only — frontend goes to Vercel separately | **API + dashboard in one service** (root `Dockerfile`) |
| Setup | One-click Blueprint — provisions the service, disk, and `JWT_SECRET` automatically | A few dashboard steps (volume, variables) |
| Cost | ~$7/mo Starter + separate frontend host | Usage-based, ~$5/mo minimum, one service total |
| Adding Redis | Separate provider (e.g. Upstash) | One click, same project |

**Why Railway is set up as a single service here:** the root `Dockerfile` builds the React dashboard and copies it into the Python image, so FastAPI serves both from one domain. That halves the hosting and makes the dashboard same-origin with the API, so it doesn't depend on CORS at all. Adding Redis is also one click, which upgrades document uploads from the inline fallback (blocking, processed in-request) to the real async Celery path.

#### Option A — Render

1. Push to GitHub → <https://render.com> → **New → Blueprint** → connect the repo.
2. Render reads `render.yaml`, creates the service, and **auto-generates `JWT_SECRET`**.
3. Fill in the values marked `sync: false` in the dashboard: `SUPABASE_*`, `OPENAI_API_KEY` (or `CLAUDE_API_KEY`), `APP_URL`, `API_URL`.
4. Upgrade the web service to the **Starter** plan (~$7/mo) so it never sleeps.

#### Option B — Railway (single service: API + dashboard)

1. Push to GitHub → <https://railway.app> → **New Project → Deploy from GitHub repo**.
2. Open the service → **Settings**:
   - **Root Directory** → leave **empty** (`/`). The build copies both `frontend/` and `backend/`, so it needs the repo root — pointing it at `backend` breaks the frontend stage.
   - **Config-as-code path** → `/railway.toml`. This must be **absolute from the repo root**; a relative `railway.toml` fails the deploy with *"service config at 'railway.toml' not found"*.
3. **Settings → Networking → Generate Domain** to get the public URL.
4. **Variables** → add everything from the [environment variable reference](#environment-variable-reference) below, plus:
   - `API_URL` and `APP_URL` → both the domain from step 3 (one service, one origin)
   - `VITE_API_URL` → the same domain. **This is read at build time**, because Vite inlines `VITE_*` into the bundle — changing it later needs a rebuild, not just a restart.
   - A real `JWT_SECRET` — Railway does not generate one for you the way Render's Blueprint does.
5. *(Recommended)* **Add a volume** mounted at `/app/chroma_data`, and set `CHROMA_PERSIST_DIR=/app/chroma_data`. Without it, uploaded documents are wiped on every redeploy.
6. *(Optional)* **+ New → Database → Redis**, then set `REDIS_URL=${{Redis.REDIS_URL}}`. To actually consume the queue, add a second service from the same repo with the start command:
   ```
   celery -A app.tasks.celery_app worker --loglevel=info --concurrency=1
   ```
   Give it the same variables. Skip this entirely if you're fine with inline upload processing.

Once deployed, the domain serves the dashboard at `/` and the API under `/api` — there is no separate frontend to deploy.

For better answer quality than open-source models on either host, set `LLM_PROVIDER=claude` and add `CLAUDE_API_KEY`.

### 3. Frontend

On **Railway** the dashboard ships inside the same service — nothing more to do.

On **Render**, deploy the frontend separately to Vercel as in Path A step 3, with `VITE_API_URL` pointing at the Render URL.

### 4. Post-deploy checklist

- [ ] `JWT_SECRET` is **not** the `.env.example` placeholder
- [ ] `USE_DEV_DB=false` and Supabase credentials are set
- [ ] `APP_URL` matches the real frontend origin
- [ ] `API_URL` matches the real backend origin — the Channels tab builds webhook callback URLs from it
- [ ] A persistent disk/volume is mounted at `CHROMA_PERSIST_DIR` (Render: in `render.yaml`; Railway: added manually) — otherwise uploaded documents vanish on redeploy
- [ ] Sign up, create a bot, upload a document, and send a test message

---

## Connecting messaging channels

Channel credentials are **per bot**, entered in the dashboard (**Bot → Channels**), not in `.env`. Each channel shows its own setup steps, a copyable callback URL and verify token, and a **Test** button that calls the provider's API and reports the real error.

The callback URLs use `API_URL`, so it must be a public HTTPS origin — providers cannot reach `localhost`. For local testing:

```bash
ngrok http 8000
```

then set `API_URL` to the ngrok URL and restart the backend.

| Channel | Needs | Notes |
|---|---|---|
| Website | nothing | Works immediately — copy the `<script>` tag |
| Slack | Bot token + signing secret | Easiest to test; no business verification |
| WhatsApp | Phone number ID + access token | Needs a Meta developer account |
| Instagram | IG account ID + access token | Needs a Business/Creator IG account linked to a Facebook Page |
| Email | Address + app password | Send-only (SMTP); no inbound polling |

---

## Environment variable reference

```bash
# ── Core ──
ENVIRONMENT=production
JWT_SECRET=<generate a long random string>
APP_URL=https://your-frontend.vercel.app
API_URL=https://your-backend.onrender.com     # or https://your-app.up.railway.app

# ── Database ──
USE_DEV_DB=false                 # true = in-memory, resets on restart
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=<anon key>
SUPABASE_SERVICE_KEY=<service role key>

# ── Vectors ──
CHROMA_MODE=embedded             # embedded | http
CHROMA_PERSIST_DIR=./chroma_data

# ── LLM (pick one) ──
# Open-source models via Together AI (OpenAI-compatible):
LLM_PROVIDER=openai
OPENAI_BASE_URL=https://api.together.xyz/v1
OPENAI_API_KEY=<your Together AI key>
OPENAI_MODEL=meta-llama/Llama-3.3-70B-Instruct-Turbo
OPENAI_VISION_MODEL=meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo

# Or Anthropic for best quality:
# LLM_PROVIDER=claude
# CLAUDE_API_KEY=sk-ant-...

# Or fully local (only where Ollama is running):
# LLM_PROVIDER=ollama
# OLLAMA_MODEL=llama3.1:8b
```

Frontend needs exactly one variable:

```bash
VITE_API_URL=https://your-backend.onrender.com   # or your Railway / HF Spaces URL
```

---

## Troubleshooting

**CORS errors in the browser** — `APP_URL` on the backend doesn't match the frontend origin. It must include the scheme and have no trailing slash.

**Widget doesn't load on a customer site** — the bot must be **Active** and have the Website channel enabled; the config endpoint returns 404 for inactive bots.

**Webhook verification fails** — the callback URL must be public HTTPS. Check `API_URL` is the deployed origin, not `localhost`.

**First request after idle is slow** — free tiers sleeping. Expected; upgrade the plan to avoid it.

**Backend won't start / build times out** — the embedding model (~2 GB with torch) needs enough RAM. Render free (512 MB) is tight; HF Spaces (16 GB) is comfortable.

**Railway: healthcheck fails on the first deploy** — cold-starting the container imports torch and loads the embedding model before Uvicorn binds. `railway.toml` sets `healthcheckTimeout = 300` for this; if it still fails, check the deploy logs for the real error rather than raising the timeout further.

**Railway: uploaded documents disappear after a deploy** — no volume is mounted. Add one at `/app/chroma_data` and set `CHROMA_PERSIST_DIR` to match. Railway volumes are dashboard-only; they can't be declared in `railway.toml`.

**Railway: `railway.toml` seems ignored** — the service's Root Directory must be set to `backend`. Railway reads the config from the service root, not the repo root.
