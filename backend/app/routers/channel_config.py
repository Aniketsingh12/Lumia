"""
Channel Configuration Router
=============================

Lets a bot owner connect a messaging channel from the dashboard by supplying
that platform's own credentials, instead of the credentials living in a global
`.env` (which allowed only one account per platform for the whole server).

Endpoints:
    GET    /api/channels/catalog                  - field schema for every channel
    GET    /api/bots/{bot_id}/channels            - this bot's channels (secrets masked)
    PUT    /api/bots/{bot_id}/channels/{channel}  - connect / update credentials
    DELETE /api/bots/{bot_id}/channels/{channel}  - disconnect
    POST   /api/bots/{bot_id}/channels/{channel}/test - live-verify the credentials

All bot-scoped routes require auth and verify the bot belongs to the caller's
organization. Secrets are accepted on write but never returned on read.
"""

import copy

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.database import get_supabase
from app.middleware.auth import get_current_user
from app.services import channel_registry as registry

# Mounted twice in main.py: once at /api/channels (catalog) and once at
# /api/bots (the bot-scoped routes), mirroring how knowledge.py is mounted.
catalog_router = APIRouter()
router = APIRouter()


def _verify_bot(bot_id: str, current_user: dict) -> dict:
    """Load a bot, ensuring it belongs to the caller's organization."""
    db = get_supabase()
    result = (
        db.table("bots")
        .select("*")
        .eq("id", bot_id)
        .eq("org_id", current_user["org_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Bot not found")
    return result.data[0]


def _webhook_url(channel: str) -> str | None:
    """Absolute callback URL the user pastes into the provider's dashboard."""
    spec = registry.CHANNELS.get(channel, {})
    if not spec.get("needs_webhook"):
        return None
    return f"{get_settings().api_url.rstrip('/')}{spec['webhook_path']}"


@catalog_router.get("/catalog")
async def get_catalog(current_user: dict = Depends(get_current_user)):
    """
    Describe every channel: its fields, help text, setup steps, and webhook URL.

    The dashboard renders its connect forms from this, so adding a channel or a
    field only requires changing the backend registry.
    """
    out = []
    for name, spec in registry.CHANNELS.items():
        out.append(
            {
                "id": name,
                "label": spec["label"],
                "description": spec["description"],
                "docs_url": spec.get("docs_url"),
                "setup_steps": spec.get("setup_steps", []),
                "needs_webhook": spec.get("needs_webhook", False),
                "webhook_url": _webhook_url(name),
                # Never expose whether a field is `generated` as editable input:
                # the UI shows generated values read-only after saving.
                "fields": [
                    {
                        "key": f["key"],
                        "label": f["label"],
                        "secret": f.get("secret", False),
                        "required": f.get("required", False),
                        "generated": f.get("generated", False),
                        "help": f.get("help", ""),
                        "default": f.get("default", ""),
                    }
                    for f in spec["fields"]
                ],
            }
        )
    return out


@router.get("/{bot_id}/channels")
async def get_bot_channels(bot_id: str, current_user: dict = Depends(get_current_user)):
    """Return this bot's channel configuration with all secrets masked."""
    bot = _verify_bot(bot_id, current_user)
    return registry.mask_channels(bot.get("channels") or {})


@router.put("/{bot_id}/channels/{channel}")
async def connect_channel(
    bot_id: str,
    channel: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    """
    Connect or update a channel's credentials.

    Blank secret fields keep the previously stored value, so the user can edit
    a phone number ID without re-pasting their access token. Webhook verify
    tokens are generated server-side on first connect.
    """
    bot = _verify_bot(bot_id, current_user)
    try:
        spec_exists = registry.get_channel(channel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Deep-copy: in dev mode the DB returns shallow copies, so mutating the
    # nested channels dict in place would corrupt the in-memory store.
    channels = copy.deepcopy(bot.get("channels") or {})
    existing = channels.get(channel) if isinstance(channels.get(channel), dict) else {}

    try:
        channels[channel] = registry.validate(channel, payload or {}, existing)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db = get_supabase()
    db.table("bots").update({"channels": channels}).eq("id", bot_id).execute()

    return {
        "channel": channel,
        "config": registry.public_view(channel, channels[channel]),
        "webhook_url": _webhook_url(channel),
        # Returned once here so the user can copy it into the provider's
        # dashboard; subsequent reads mask it like any other secret.
        "verify_token": channels[channel].get("verify_token")
        if spec_exists.get("needs_webhook")
        else None,
    }


@router.delete("/{bot_id}/channels/{channel}")
async def disconnect_channel(
    bot_id: str,
    channel: str,
    current_user: dict = Depends(get_current_user),
):
    """Disconnect a channel and delete its stored credentials."""
    bot = _verify_bot(bot_id, current_user)
    channels = copy.deepcopy(bot.get("channels") or {})
    channels.pop(channel, None)

    db = get_supabase()
    db.table("bots").update({"channels": channels}).eq("id", bot_id).execute()
    return {"channel": channel, "connected": False}


@router.post("/{bot_id}/channels/{channel}/test")
async def test_channel(
    bot_id: str,
    channel: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Verify stored credentials by calling the provider's API.

    Returns {ok: bool, detail: str} rather than raising, so the dashboard can
    show the provider's own error message (expired token, wrong ID, ...).
    """
    bot = _verify_bot(bot_id, current_user)
    creds = registry.resolve_credentials(bot, channel)

    try:
        if channel == "website":
            return {"ok": True, "detail": "Website widget needs no credentials."}
        if channel == "whatsapp":
            return await _test_whatsapp(creds)
        if channel == "instagram":
            return await _test_instagram(creds)
        if channel == "slack":
            return await _test_slack(creds)
        if channel == "email":
            return _test_email(creds)
        raise HTTPException(status_code=400, detail=f"Unknown channel: {channel}")
    except HTTPException:
        raise
    except Exception as exc:  # never let a provider outage 500 the dashboard
        return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}


async def _test_whatsapp(creds: dict) -> dict:
    phone_id = creds.get("phone_number_id")
    token = creds.get("access_token")
    if not phone_id or not token:
        return {"ok": False, "detail": "Phone number ID and access token are required."}

    version = get_settings().graph_api_version
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"https://graph.facebook.com/{version}/{phone_id}",
            params={"fields": "display_phone_number,verified_name"},
            headers={"Authorization": f"Bearer {token}"},
        )
    if r.status_code == 200:
        d = r.json()
        name = d.get("verified_name", "")
        number = d.get("display_phone_number", "")
        return {"ok": True, "detail": f"Connected to {name} ({number})".strip()}
    return {"ok": False, "detail": _meta_error(r)}


async def _test_instagram(creds: dict) -> dict:
    token = creds.get("access_token")
    if not token:
        return {"ok": False, "detail": "Access token is required."}

    version = get_settings().graph_api_version
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"https://graph.facebook.com/{version}/me",
            params={"fields": "id,name"},
            headers={"Authorization": f"Bearer {token}"},
        )
    if r.status_code == 200:
        d = r.json()
        return {"ok": True, "detail": f"Token valid for {d.get('name') or d.get('id')}"}
    return {"ok": False, "detail": _meta_error(r)}


async def _test_slack(creds: dict) -> dict:
    token = creds.get("bot_token")
    if not token:
        return {"ok": False, "detail": "Bot token is required."}

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://slack.com/api/auth.test",
            headers={"Authorization": f"Bearer {token}"},
        )
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if data.get("ok"):
        return {
            "ok": True,
            "detail": f"Connected to {data.get('team')} as {data.get('user')}",
        }
    return {"ok": False, "detail": data.get("error") or f"HTTP {r.status_code}"}


def _test_email(creds: dict) -> dict:
    import smtplib

    address = creds.get("address")
    password = creds.get("app_password")
    if not address or not password:
        return {"ok": False, "detail": "Email address and app password are required."}

    host = creds.get("smtp_host") or "smtp.gmail.com"
    try:
        port = int(creds.get("smtp_port") or 587)
    except (TypeError, ValueError):
        port = 587

    with smtplib.SMTP(host, port, timeout=15) as server:
        server.starttls()
        server.login(address, password)
    return {"ok": True, "detail": f"SMTP login succeeded for {address}"}


def _meta_error(response: httpx.Response) -> str:
    """Pull Meta's human-readable message out of a Graph API error body."""
    try:
        return response.json().get("error", {}).get("message") or f"HTTP {response.status_code}"
    except Exception:
        return f"HTTP {response.status_code}"
