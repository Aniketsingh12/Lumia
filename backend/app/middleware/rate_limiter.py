"""
Abuse Protection for Public Chat Endpoints
============================================

POST /api/chat/, /agent, /stream and WS /ws/{id} are deliberately public — an
anonymous website visitor must be able to use the embeddable widget without
creating an account. That openness is exactly what lets anyone who has (or
guesses) a bot_id call the LLM directly and run up costs. Gating those
endpoints behind login would stop the abuse but also break every legitimate
visitor, since a site visitor can't be expected to sign up mid-chat.

Instead, two independent, free caps bound the damage:

  - check_rate_limit() — per-IP request rate. Stops a single script/browser
    from hammering the endpoint. Scoped (e.g. "chat" vs "auth") so heavy
    chat use never blocks that same visitor from logging into the dashboard.
  - check_bot_quota()  — per-bot daily AI-reply count. Stops abuse that
    rotates IPs, and puts a hard ceiling on worst-case spend for any one bot
    regardless of where the traffic comes from. This is the cap that
    actually protects the token/credit budget.

Both prefer Redis (correct across restarts and multiple instances) when
REDIS_URL is actually reachable, and transparently fall back to an in-process
in-memory counter otherwise. This deployment runs as a single instance by
default, so the in-memory path is a fully adequate, zero-infrastructure
default — not a stopgap. It mirrors the same reachability-probe-then-fallback
pattern already used for Celery/Redis in routers/knowledge.py.
"""

import time
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import get_settings

_redis_client = None


def _redis_reachable(timeout: float = 0.2) -> bool:
    """Best-effort, tightly-bounded probe — see knowledge.py's identical pattern."""
    import socket
    from urllib.parse import urlparse

    try:
        parsed = urlparse(get_settings().redis_url)
        addr = (parsed.hostname or "localhost", parsed.port or 6379)
        with socket.create_connection(addr, timeout=timeout):
            return True
    except OSError:
        return False


def _get_redis():
    global _redis_client
    if _redis_client is None:
        import redis

        _redis_client = redis.from_url(get_settings().redis_url)
    return _redis_client


def _incr_redis(key: str, window_seconds: int) -> int:
    r = _get_redis()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    return pipe.execute()[0]


# ---------------------------------------------------------------------------
# In-memory fallback — a fixed window keyed by `now // window_seconds`.
# Unix epoch starts at UTC midnight, so a 86400s window lines up exactly with
# UTC calendar days for free. No background cleanup needed: a stale key is
# simply overwritten (count reset) the next time that key is seen.
# ---------------------------------------------------------------------------
_windows: dict[str, tuple[int, int]] = {}


def _incr_memory(key: str, window_seconds: int) -> int:
    bucket = int(time.time()) // window_seconds
    stored_bucket, count = _windows.get(key, (bucket, 0))
    if stored_bucket != bucket:
        count = 0
    count += 1
    _windows[key] = (bucket, count)
    return count


def _incr(key: str, window_seconds: int) -> int:
    if _redis_reachable():
        try:
            return _incr_redis(key, window_seconds)
        except Exception:
            pass  # Redis flaked mid-request — fall back rather than 500 the caller
    return _incr_memory(key, window_seconds)


# ---------------------------------------------------------------------------
# Public checks
# ---------------------------------------------------------------------------


async def check_rate_limit(
    client_ip: str, *, scope: str = "chat", limit: int | None = None, window: int = 60
) -> None:
    """
    Raise 429 once `client_ip` exceeds `limit` requests (default:
    settings.rate_limit_per_minute) within `window` seconds for this `scope`.

    Call this first, before any LLM/DB work, on every public chat endpoint.
    """
    settings = get_settings()
    effective_limit = limit if limit is not None else settings.rate_limit_per_minute
    count = _incr(f"ratelimit:{scope}:{client_ip}", window)
    if count > effective_limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests sent too quickly. Please wait a moment and try again.",
        )


async def check_bot_quota(bot_id: str) -> None:
    """
    Raise 429 once `bot_id` exceeds `settings.bot_daily_message_limit` AI
    replies for the current UTC day.
    """
    settings = get_settings()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = _incr(f"botquota:{bot_id}:{today}", 86400)
    if count > settings.bot_daily_message_limit:
        raise HTTPException(
            status_code=429,
            detail="This bot has reached its message limit for today. Please try again tomorrow.",
        )
