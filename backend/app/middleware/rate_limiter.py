import time
import redis
from fastapi import Request, HTTPException

from app.config import get_settings

_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(settings.redis_url)
    return _redis_client


async def rate_limit(request: Request, limit: int = 60, window: int = 60):
    """Rate limit by IP address. Default: 60 requests per minute."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:{client_ip}"

    r = get_redis()
    current = r.get(key)

    if current and int(current) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests")

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    pipe.execute()
