"""
=============================================================================
BotForge — config.py (CONFIGURATION / SETTINGS)
=============================================================================

THIS FILE LOADS ALL ENVIRONMENT VARIABLES FROM THE .env FILE.

Instead of hardcoding API keys and URLs in code (which is insecure and inflexible),
we store them in a .env file and load them here using Pydantic Settings.

HOW IT WORKS:
1. Pydantic's BaseSettings reads from environment variables automatically
2. Variable names in the class map to .env variable names (case-insensitive)
3. Example: `claude_api_key` reads from CLAUDE_API_KEY in .env
4. Default values are used if the variable is not set

WHY @lru_cache ON get_settings()?
  - lru_cache means "call this function once, then reuse the result forever"
  - Without it, every call to get_settings() would re-read the .env file
  - With it, the .env is read once and cached — much faster

USAGE THROUGHOUT THE APP:
  from app.config import get_settings
  settings = get_settings()
  print(settings.claude_api_key)  # Reads CLAUDE_API_KEY from .env
=============================================================================
"""

from pydantic_settings import BaseSettings  # Pydantic v2 settings management
from functools import lru_cache  # Caches function results for performance


class Settings(BaseSettings):
    """
    All configuration for BotForge.
    Each field maps to an environment variable (case-insensitive).
    Example: supabase_url → reads SUPABASE_URL from .env
    """

    # ── SUPABASE (Database + Auth + Storage) ──
    # Get these from: Supabase Dashboard → Settings → API
    supabase_url: str = ""  # Your Supabase project URL
    supabase_key: str = ""  # The "anon" public key (safe for client-side)
    supabase_service_key: str = ""  # The "service_role" key (admin access, server-only!)

    # ── LLM PROVIDER ──
    # Which AI model to use for generating answers
    # Options: "claude" (Anthropic), "openai" (GPT), "ollama" (free local models)
    llm_provider: str = "claude"
    claude_api_key: str = ""  # From: console.anthropic.com
    openai_api_key: str = ""  # From: platform.openai.com
    # Custom OpenAI-compatible endpoint. Leave blank for real OpenAI. Set this to
    # point the "openai" provider at any OpenAI-compatible API — e.g. Together AI
    # (https://api.together.xyz/v1), OpenRouter, Fireworks, or a self-hosted
    # vLLM/LM Studio server. This is how we serve free open-source models
    # (Llama, etc.) in deployment without running Ollama on the server.
    openai_base_url: str = ""
    ollama_base_url: str = "http://localhost:11434"  # Default Ollama local server

    # Model names — overridable per provider so you can swap to any
    # open-source / hosted model without code changes.
    claude_model: str = "claude-sonnet-4-20250514"
    claude_vision_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4o"
    openai_vision_model: str = "gpt-4o"
    ollama_model: str = "llama3.1"          # text chat, e.g. "llama3.1", "mistral", "qwen2.5"
    ollama_vision_model: str = "llava"      # vision, e.g. "llava", "llama3.2-vision", "bakllava"

    # ── EMBEDDINGS ──
    # Local sentence-transformers model (runs on CPU, fully offline / free).
    embedding_model: str = "all-MiniLM-L6-v2"

    # ── VOICE / SPEECH-TO-TEXT ──
    # "openai"          — OpenAI Whisper API (requires OPENAI_API_KEY)
    # "local"           — faster-whisper running locally (free, requires `pip install faster-whisper`)
    voice_provider: str = "openai"
    local_whisper_model: str = "base"  # tiny | base | small | medium | large-v3

    # ── REDIS (Cache + Task Queue) ──
    # Redis is used for: rate limiting, caching, and Celery task queue
    redis_url: str = "redis://localhost:6379/0"

    # ── CHROMADB (Vector Database) ──
    # ChromaDB stores document embeddings for RAG (Retrieval-Augmented Generation).
    # Two modes:
    #   "embedded" — runs in-process, persists to chroma_persist_dir on disk.
    #                No separate server needed. Best for local dev / single-node.
    #   "http"     — connects to a standalone ChromaDB server (chroma_host:chroma_port),
    #                which must be started separately (`chroma run --port 8001`).
    chroma_mode: str = "embedded"  # "embedded" | "http"
    chroma_persist_dir: str = "./chroma_data"  # where embedded mode stores vectors
    chroma_host: str = "localhost"
    chroma_port: int = 8001  # Note: ChromaDB runs on 8001 to avoid conflict with FastAPI on 8000

    # ── JWT (JSON Web Tokens for Authentication) ──
    # JWT tokens are how we track logged-in users
    jwt_secret: str = "change-this-secret"  # MUST change in production!
    jwt_algorithm: str = "HS256"  # Hashing algorithm for token signing
    jwt_expiration_hours: int = 24  # Token expires after 24 hours

    # ── ABUSE PROTECTION ──
    # The chat endpoints are deliberately public (no login) so an anonymous
    # website visitor can use the embeddable widget. See middleware/rate_limiter.py
    # for how these two independent caps bound LLM cost without requiring auth.
    rate_limit_per_minute: int = 20     # max chat requests per IP per 60s
    bot_daily_message_limit: int = 300  # max AI replies per bot per UTC day

    # ── META GRAPH API ──
    # Version used for all WhatsApp/Instagram Graph calls. Meta retires versions
    # roughly two years after release, so keep this current and change it in one
    # place rather than hardcoding it at each call site.
    graph_api_version: str = "v21.0"

    # ── WHATSAPP (Meta Business API) ──
    # NOTE: these globals are now a FALLBACK only. Channels are normally
    # configured per-bot from the dashboard (see services/channel_registry.py).
    # Required to send/receive WhatsApp messages
    whatsapp_token: str = ""  # Permanent token from Meta Developer Portal
    whatsapp_verify_token: str = ""  # Random string YOU choose for webhook verification
    whatsapp_phone_number_id: str = ""  # Your WhatsApp Business phone number ID

    # ── INSTAGRAM (Meta Graph API) ──
    instagram_token: str = ""  # Page access token with instagram_messaging permission
    instagram_verify_token: str = ""  # Random string for webhook verification

    # ── SLACK (Bolt SDK) ──
    slack_bot_token: str = ""  # Starts with "xoxb-" — from Slack app settings
    slack_signing_secret: str = ""  # Verifies requests actually come from Slack

    # ── EMAIL (IMAP/SMTP for reading/sending emails) ──
    email_imap_host: str = "imap.gmail.com"  # For reading incoming emails
    email_imap_port: int = 993  # IMAP over SSL
    email_smtp_host: str = "smtp.gmail.com"  # For sending reply emails
    email_smtp_port: int = 587  # SMTP with TLS
    email_address: str = ""  # The email address the bot uses
    email_password: str = ""  # App password (NOT your regular password!)

    # ── APPLICATION URLS ──
    app_url: str = "http://localhost:5173"  # Frontend React app URL
    api_url: str = "http://localhost:8000"  # Backend API URL
    environment: str = "development"  # "development" or "production"

    # ── DEV MODE ──
    # Set USE_DEV_DB=true to use the in-memory shim (app/dev_db.py) even when
    # real Supabase credentials are present. Useful for local dev without network.
    use_dev_db: bool = False

    # Pydantic model config: tells it where to find the .env file
    # "extra": "ignore" means don't crash if .env has variables not listed above
    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache  # Cache the result — only creates Settings object ONCE
def get_settings() -> Settings:
    """
    Get application settings (cached singleton).
    Call this anywhere in the app to access config values.
    The first call reads .env file; subsequent calls return the cached result.
    """
    return Settings()
