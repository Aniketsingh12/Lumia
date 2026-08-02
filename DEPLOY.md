# Deploying Lumio

Two paths, depending on what you need:

- **[Path A — Free portfolio deploy](#path-a--free-portfolio-deploy)** ($0/mo, sleeps when idle) — for a demo link recruiters and prospective clients can click.
- **[Path B — Production deploy](#path-b--production-deploy)** (~$7/mo, always on) — for a real client whose customers depend on it.

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
| LLM | **Groq** — Llama 3.1, OpenAI-compatible, very fast | Free |
| Backend | **Hugging Face Spaces** (Docker, 16 GB RAM) | Free |
| Frontend | **Vercel** | Free |
| Database | in-memory dev DB (`USE_DEV_DB=true`) | Free |
| Vectors | embedded ChromaDB | Free |

### 1. Get a free Groq API key

Sign up at <https://console.groq.com> (no card required) and create a key — it looks like `gsk_...`. Groq serves the same open-source Llama models you can run locally with Ollama, but responses land in well under a second instead of ~20s on CPU.

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
   | `OPENAI_BASE_URL` | `https://api.groq.com/openai/v1` |
   | `OPENAI_API_KEY` | your `gsk_...` key — add as a **secret** |
   | `OPENAI_MODEL` | `llama-3.1-8b-instant` |
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
- **Groq free has rate limits** — fine for a demo, not for real traffic.

---

## Path B — Production deploy

Use this once a real client depends on it. Free tiers sleep, rate-limit, and offer no uptime guarantee — that's fine for a portfolio, not for someone's customers.

### 1. Database — Supabase

1. Create a project at <https://supabase.com>.
2. Run `scripts/migrate.py`, or paste the SQL schema from `docs/architecture.md` into the SQL editor.
3. Copy the project URL, anon key, and service-role key.
4. Set `USE_DEV_DB=false`.

### 2. Backend — Render (one-click)

`render.yaml` is a Blueprint that provisions everything, including a 1 GB persistent disk so the ChromaDB knowledge base survives redeploys.

1. Push to GitHub → <https://render.com> → **New → Blueprint** → connect the repo.
2. Render reads `render.yaml`, creates the service, and **auto-generates `JWT_SECRET`**.
3. Fill in the values marked `sync: false` in the dashboard: `SUPABASE_*`, `OPENAI_API_KEY` (or `CLAUDE_API_KEY`), `APP_URL`, `API_URL`.
4. Upgrade the web service to the **Starter** plan (~$7/mo) so it never sleeps.

For better answer quality than free Llama, set `LLM_PROVIDER=claude` and add `CLAUDE_API_KEY`.

### 3. Frontend — Vercel

Same as Path A step 3, with `VITE_API_URL` pointing at the Render URL.

### 4. Post-deploy checklist

- [ ] `JWT_SECRET` is **not** the `.env.example` placeholder
- [ ] `USE_DEV_DB=false` and Supabase credentials are set
- [ ] `APP_URL` matches the real frontend origin
- [ ] `API_URL` matches the real backend origin — the Channels tab builds webhook callback URLs from it
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
API_URL=https://your-backend.onrender.com

# ── Database ──
USE_DEV_DB=false                 # true = in-memory, resets on restart
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=<anon key>
SUPABASE_SERVICE_KEY=<service role key>

# ── Vectors ──
CHROMA_MODE=embedded             # embedded | http
CHROMA_PERSIST_DIR=./chroma_data

# ── LLM (pick one) ──
# Free, fast, open-source models via Groq:
LLM_PROVIDER=openai
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=gsk_...
OPENAI_MODEL=llama-3.1-8b-instant

# Or Anthropic for best quality:
# LLM_PROVIDER=claude
# CLAUDE_API_KEY=sk-ant-...

# Or fully local (only where Ollama is running):
# LLM_PROVIDER=ollama
# OLLAMA_MODEL=llama3.1:8b
```

Frontend needs exactly one variable:

```bash
VITE_API_URL=https://your-backend.onrender.com
```

---

## Troubleshooting

**CORS errors in the browser** — `APP_URL` on the backend doesn't match the frontend origin. It must include the scheme and have no trailing slash.

**Widget doesn't load on a customer site** — the bot must be **Active** and have the Website channel enabled; the config endpoint returns 404 for inactive bots.

**Webhook verification fails** — the callback URL must be public HTTPS. Check `API_URL` is the deployed origin, not `localhost`.

**First request after idle is slow** — free tiers sleeping. Expected; upgrade the plan to avoid it.

**Backend won't start / build times out** — the embedding model (~2 GB with torch) needs enough RAM. Render free (512 MB) is tight; HF Spaces (16 GB) is comfortable.
