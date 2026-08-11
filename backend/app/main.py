"""
=============================================================================
BotForge — main.py (APPLICATION ENTRY POINT)
=============================================================================

THIS IS THE STARTING POINT OF THE ENTIRE BACKEND.

When you run: uvicorn app.main:app --reload
Python executes this file first. It creates the FastAPI application object
and wires together ALL the pieces:

WHAT THIS FILE DOES:
1. Creates the FastAPI app (like creating a new Express app in Node.js)
2. Sets up CORS (so the React frontend at :5173 can talk to backend at :8000)
3. Registers ALL API routes (auth, bots, chat, etc.)
4. Registers channel webhooks (WhatsApp, Instagram, Slack, Email)
5. Sets up error handlers for clean error responses
6. Defines startup/shutdown lifecycle events

FLOW:
  uvicorn runs this file
    → FastAPI app is created
    → CORS middleware added (allows frontend cross-origin requests)
    → All routers are registered with their URL prefixes
    → App starts listening on port 8000
    → When a request comes in, FastAPI routes it to the correct handler

WHY FASTAPI?
  - Async by default (handles many requests simultaneously)
  - Auto-generates API docs at /docs (Swagger UI)
  - Built-in request validation via Pydantic models
  - Native WebSocket support for real-time chat
=============================================================================
"""

import os
from contextlib import asynccontextmanager  # For managing app startup/shutdown

from fastapi import FastAPI, HTTPException  # The web framework
from fastapi.middleware.cors import CORSMiddleware  # Cross-Origin Resource Sharing
from fastapi.responses import FileResponse  # For serving widget.js and the dashboard
from fastapi.staticfiles import StaticFiles  # For serving the built dashboard assets

# Import our configuration (loads .env file)
from app.config import get_settings

# Import our custom error handler
from app.middleware.error_handler import register_error_handlers

# Import all route handlers — each file handles a group of related endpoints
from app.routers import (
    analytics,
    auth,
    bots,
    channel_config,
    chat,
    conversations,
    knowledge,
    settings,
    widget,
)

# Import channel-specific webhook handlers
from app.routers.channels import email, instagram, slack, whatsapp


# ── LIFESPAN: Startup & Shutdown Events ──
# This runs code when the server starts and when it stops.
# "async with" pattern: code before "yield" runs on startup, after "yield" on shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP ===
    # This code runs ONCE when the server starts
    settings = get_settings()
    from app.database import _is_dev_mode
    if _is_dev_mode():
        print("[DEV MODE] using in-memory database (no Supabase)")
        print("   Test accounts ready:")
        print("     admin@botforge.dev / admin123")
        print("     demo@botforge.app  / demo123")
        print("     test@test.com      / test123")
        print("   Sign up with any email to create a new account.")
    print(f"[startup] Lumio API starting in {settings.environment} mode")
    # You could initialize database connections, load ML models, etc. here

    yield  # Server is now running and accepting requests

    # === SHUTDOWN ===
    # This code runs ONCE when the server stops (Ctrl+C or deployment restart)
    print("[shutdown] Lumio API shutting down")
    # You could close database connections, flush caches, etc. here


# ── CREATE THE FASTAPI APPLICATION ──
# This is the main app object. Everything attaches to this.
# FastAPI auto-generates interactive API docs at:
#   - http://localhost:8000/docs  (Swagger UI)
#   - http://localhost:8000/redoc (ReDoc)
app = FastAPI(
    title="Lumio API",  # Shows in the auto-generated docs
    description="AI Chat Platform — Build intelligent chatbots with RAG",
    version="1.0.0",
    lifespan=lifespan,  # Attach our startup/shutdown handler
)


# ── CORS MIDDLEWARE ──
# CORS = Cross-Origin Resource Sharing. The browser blocks cross-origin requests
# unless the server opts in with these headers.
#
# We allow ALL origins because the embeddable chat widget (widget.js) runs on
# arbitrary customer websites and must be able to call /api/chat/ and
# /api/widget/* from any domain. This is safe here because authentication uses a
# Bearer token stored in localStorage (sent as an explicit Authorization header),
# NOT cookies — so we set allow_credentials=False. A malicious site still can't
# read another origin's localStorage, so it can't forge authenticated calls, and
# with credentials disabled there are no cookies to ride on. (If auth ever moves
# to cookies, this must be tightened to an allow-list of trusted origins.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers (Authorization, Content-Type, etc.)
)

# ── ERROR HANDLERS ──
# Catches unhandled exceptions and returns clean JSON errors instead of ugly stack traces
register_error_handlers(app)


# ── REGISTER API ROUTES ──
# Each "router" is a collection of related endpoints.
# The "prefix" defines the URL path, "tags" group them in the docs.
#
# Example: auth.router has POST /signup → becomes POST /api/auth/signup
# Example: bots.router has GET / → becomes GET /api/bots/

# Core application routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(bots.router, prefix="/api/bots", tags=["Bots"])
app.include_router(knowledge.router, prefix="/api/bots", tags=["Knowledge Base"])
# Per-bot channel credentials: /api/bots/{id}/channels/... plus the shared
# field catalog the dashboard renders its connect forms from.
app.include_router(channel_config.router, prefix="/api/bots", tags=["Channels"])
app.include_router(channel_config.catalog_router, prefix="/api/channels", tags=["Channels"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["Conversations"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(widget.router, prefix="/api/widget", tags=["Widget"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])

# Channel webhook routes — these receive messages FROM external platforms
# When someone sends a WhatsApp message → Meta calls our webhook → we process it
app.include_router(whatsapp.router, prefix="/api/channels/whatsapp", tags=["WhatsApp"])
app.include_router(instagram.router, prefix="/api/channels/instagram", tags=["Instagram"])
app.include_router(slack.router, prefix="/api/channels/slack", tags=["Slack"])
app.include_router(email.router, prefix="/api/channels/email", tags=["Email"])


# ── EMBEDDABLE WIDGET LOADER ──
# GET http://localhost:8000/widget.js
# This is the script that customer websites embed:
#   <script src="<API_URL>/widget.js" data-bot-id="<uuid>"></script>
# It's served from the app root (not under /api) so the embed snippet is short.
# The file itself lives in app/static/widget.js and renders the chat bubble.
_WIDGET_JS_PATH = os.path.join(os.path.dirname(__file__), "static", "widget.js")


@app.get("/widget.js")
async def widget_js():
    # 5-minute cache so repeat page loads don't re-fetch, but updates still
    # roll out quickly. media_type must be JS or browsers refuse to run it.
    return FileResponse(
        _WIDGET_JS_PATH,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )


# ── HEALTH CHECK ──
# GET http://localhost:8000/health
# Used by monitoring tools and load balancers to check if the server is alive
@app.get("/health")
async def health():
    return {"status": "healthy"}


# ── SINGLE-SERVICE FRONTEND HOSTING ──
# In deployment we ship ONE service: the Docker build compiles the React
# dashboard and drops it here, and this app serves it alongside the API. That
# means one domain and one bill, and — because the dashboard is then same-origin
# with the API — no CORS involvement for the dashboard at all.
#
# When the directory is absent (local dev with `npm run dev`, and in tests) every
# route below degrades to the original API-only behaviour, so nothing changes for
# development.
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "static_frontend")
_FRONTEND_INDEX = os.path.join(_FRONTEND_DIR, "index.html")
_SERVE_FRONTEND = os.path.isfile(_FRONTEND_INDEX)

if _SERVE_FRONTEND:
    # Vite emits hashed filenames under /assets and fingerprints them, so they
    # are safe to cache hard. index.html itself must NOT be cached that way or
    # browsers would keep loading an old build after a deploy.
    _ASSETS_DIR = os.path.join(_FRONTEND_DIR, "assets")
    if os.path.isdir(_ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")


@app.get("/")
async def root():
    """Serve the dashboard when it's bundled in; otherwise report API status."""
    if _SERVE_FRONTEND:
        return FileResponse(_FRONTEND_INDEX)
    return {"name": "Lumio API", "version": "1.0.0", "status": "running"}


if _SERVE_FRONTEND:

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """
        Catch-all that backs the dashboard's client-side routing.

        Registered last, so every real API route, /docs and /widget.js are
        matched first and never reach this. A request for a path that exists as
        a built file (favicon, etc.) returns that file; anything else returns
        index.html so React Router can resolve routes like /dashboard or
        /bots/:id on a refresh or deep link.
        """
        # An unmatched /api/... path is a genuinely missing endpoint. Without
        # this guard it would return index.html with a 200, so a typo'd API call
        # would look "successful" to the client and fail confusingly later.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        # Resolve against the frontend dir and confirm the result stays inside
        # it, so encoded traversal (e.g. ../../etc/passwd) can't escape.
        candidate = os.path.normpath(os.path.join(_FRONTEND_DIR, full_path))
        if (
            full_path
            and candidate.startswith(os.path.normpath(_FRONTEND_DIR) + os.sep)
            and os.path.isfile(candidate)
        ):
            return FileResponse(candidate)

        return FileResponse(_FRONTEND_INDEX)
