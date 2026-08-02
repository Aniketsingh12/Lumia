"""
Channel Registry
=================

Single source of truth for what credentials each messaging channel needs, how to
validate them, how to hide the secret ones from API responses, and how to find
the bot that owns an incoming webhook.

Why this exists
---------------
Channel credentials used to live in the global `.env`, which meant:
  - only ONE WhatsApp/Instagram/Slack account could ever be connected,
  - the webhook had to guess the bot ("first active bot with the flag set"),
  - a customer could not connect their own account from the dashboard.

Credentials now live per-bot inside the bot's `channels` JSON column:

    channels = {
      "website":  {"connected": true},
      "whatsapp": {"connected": true,
                   "phone_number_id": "123", "access_token": "...",
                   "verify_token": "..."},
      ...
    }

The `.env` values are still honoured as a fallback so existing single-tenant
setups keep working (see `resolve_credentials`).

Secrets
-------
Fields marked `secret` are never returned by the API. `public_view()` replaces
them with a `<field>_set: true/false` flag so the dashboard can show "configured"
without ever shipping the token to the browser.
"""

import secrets as _secrets
from typing import Any

# ---------------------------------------------------------------------------
# Field definitions
# ---------------------------------------------------------------------------
# Each field: key, label, secret?, required?, help text, optional default.
# `generated: True` means the backend creates the value on connect (the user
# copies it into the provider's dashboard rather than inventing it themselves).

CHANNELS: dict[str, dict[str, Any]] = {
    "website": {
        "label": "Website Widget",
        "description": "Embed a chat bubble on any website. No credentials needed.",
        "docs_url": None,
        "needs_webhook": False,
        "fields": [],
    },
    "whatsapp": {
        "label": "WhatsApp",
        "description": "Reply to WhatsApp messages via the Meta Cloud API.",
        "docs_url": "https://developers.facebook.com/docs/whatsapp/cloud-api/get-started",
        "needs_webhook": True,
        "webhook_path": "/api/channels/whatsapp/webhook",
        "setup_steps": [
            "Create a Business app at developers.facebook.com and add the WhatsApp product.",
            "On the API Setup page copy the Phone number ID and the temporary access token.",
            "Paste them here and save — we'll generate your verify token.",
            "Back in Meta → WhatsApp → Configuration, set the Callback URL and Verify token "
            "shown below, then subscribe to the 'messages' field.",
        ],
        "fields": [
            {
                "key": "phone_number_id",
                "label": "Phone number ID",
                "secret": False,
                "required": True,
                "help": "Meta → WhatsApp → API Setup. A long number, not the phone number itself.",
            },
            {
                "key": "access_token",
                "label": "Access token",
                "secret": True,
                "required": True,
                "help": "Temporary tokens expire in 24h; use a System User token for permanence.",
            },
            {
                "key": "verify_token",
                "label": "Webhook verify token",
                "secret": True,
                "required": True,
                "generated": True,
                "help": "Generated for you. Paste this into Meta's webhook configuration.",
            },
        ],
    },
    "instagram": {
        "label": "Instagram DMs",
        "description": "Auto-reply to Instagram Direct Messages.",
        "docs_url": "https://developers.facebook.com/docs/messenger-platform/instagram",
        "needs_webhook": True,
        "webhook_path": "/api/channels/instagram/webhook",
        "setup_steps": [
            "Switch the Instagram account to Business or Creator and link a Facebook Page.",
            "In your Meta app add the Messenger product and connect that Page.",
            "Generate a token with the instagram_manage_messages permission and paste it here.",
            "In Meta → Messenger → Instagram Settings → Webhooks, set the Callback URL and "
            "Verify token shown below and subscribe to 'messages'.",
        ],
        "fields": [
            {
                "key": "ig_user_id",
                "label": "Instagram account ID",
                "secret": False,
                "required": True,
                "help": "The Instagram-scoped business account ID (a long number).",
            },
            {
                "key": "access_token",
                "label": "Access token",
                "secret": True,
                "required": True,
                "help": "Page access token carrying instagram_manage_messages.",
            },
            {
                "key": "verify_token",
                "label": "Webhook verify token",
                "secret": True,
                "required": True,
                "generated": True,
                "help": "Generated for you. Paste this into Meta's webhook configuration.",
            },
        ],
    },
    "slack": {
        "label": "Slack",
        "description": "Answer messages in your Slack workspace.",
        "docs_url": "https://api.slack.com/apps",
        "needs_webhook": True,
        "webhook_path": "/api/channels/slack/events",
        "setup_steps": [
            "Create an app at api.slack.com/apps (From scratch).",
            "OAuth & Permissions → add scopes chat:write, channels:history, app_mentions:read "
            "→ Install to Workspace.",
            "Paste the Bot User OAuth Token (xoxb-…) and the Signing Secret here.",
            "Event Subscriptions → set the Request URL below, then subscribe to "
            "'message.channels'. Slack verifies the URL live, so save here first.",
        ],
        "fields": [
            {
                "key": "bot_token",
                "label": "Bot user OAuth token",
                "secret": True,
                "required": True,
                "help": "Starts with xoxb-. From OAuth & Permissions after installing the app.",
            },
            {
                "key": "signing_secret",
                "label": "Signing secret",
                "secret": True,
                "required": True,
                "help": "Basic Information → App Credentials. Verifies that "
                        "requests really come from Slack.",
            },
            {
                "key": "team_id",
                "label": "Workspace ID",
                "secret": False,
                "required": False,
                "help": "Optional (e.g. T01ABCDEF). Set it to route one "
                        "workspace to this bot.",
            },
        ],
    },
    "email": {
        "label": "Email",
        "description": "Send replies from your support inbox over SMTP.",
        "docs_url": "https://support.google.com/accounts/answer/185833",
        "needs_webhook": False,
        "fields": [
            {
                "key": "address",
                "label": "Email address",
                "secret": False,
                "required": True,
                "help": "The mailbox replies are sent from.",
            },
            {
                "key": "app_password",
                "label": "App password",
                "secret": True,
                "required": True,
                "help": "For Gmail: enable 2FA, then create an App Password. "
                        "Not your normal login password.",
            },
            {
                "key": "smtp_host",
                "label": "SMTP host",
                "secret": False,
                "required": False,
                "default": "smtp.gmail.com",
                "help": "",
            },
            {
                "key": "smtp_port",
                "label": "SMTP port",
                "secret": False,
                "required": False,
                "default": "587",
                "help": "587 for STARTTLS.",
            },
        ],
    },
}


def get_channel(channel: str) -> dict[str, Any]:
    """Return the definition for a channel, or raise ValueError if unknown."""
    if channel not in CHANNELS:
        raise ValueError(f"Unknown channel: {channel}")
    return CHANNELS[channel]


def generate_verify_token() -> str:
    """A URL-safe random token the user pastes into the provider's dashboard."""
    return _secrets.token_urlsafe(24)


def validate(
    channel: str, submitted: dict[str, Any], existing: dict[str, Any] | None = None
) -> dict:
    """
    Validate and normalize submitted credentials for `channel`.

    Rules:
      - Unknown keys are dropped (so a stale frontend can't inject junk).
      - Required fields must end up non-empty, EITHER from this submission or
        from previously stored values (so the user can edit non-secret fields
        without re-typing their token).
      - Blank submissions for a secret keep the previously stored secret.
      - `generated` fields are auto-created when missing.

    Returns the dict to persist (raw secrets included).
    Raises ValueError listing any missing required fields.
    """
    spec = get_channel(channel)
    existing = existing or {}
    out: dict[str, Any] = {}

    for field in spec["fields"]:
        key = field["key"]
        value = submitted.get(key)
        if isinstance(value, str):
            value = value.strip()

        # Empty submission → fall back to what's already stored, then default.
        if not value:
            value = existing.get(key) or field.get("default") or ""

        # Auto-generate (e.g. webhook verify tokens) when still empty.
        if not value and field.get("generated"):
            value = generate_verify_token()

        if value:
            out[key] = value

    missing = [
        f["label"]
        for f in spec["fields"]
        if f.get("required") and not out.get(f["key"])
    ]
    if missing:
        raise ValueError("Missing required field(s): " + ", ".join(missing))

    out["connected"] = True
    return out


def public_view(channel: str, stored: Any) -> dict[str, Any]:
    """
    Strip secrets from a stored channel config for safe return over the API.

    Every secret field becomes `<key>_set: bool` instead of its value, so the UI
    can render "configured" without the token ever reaching the browser.
    """
    # Legacy rows stored a bool (website) or the string "pending_setup".
    if not isinstance(stored, dict):
        return {"connected": bool(stored)}

    spec = CHANNELS.get(channel)
    if spec is None:
        return {"connected": bool(stored.get("connected"))}

    view: dict[str, Any] = {"connected": bool(stored.get("connected"))}
    for field in spec["fields"]:
        key = field["key"]
        if field.get("secret"):
            view[f"{key}_set"] = bool(stored.get(key))
        elif stored.get(key):
            view[key] = stored[key]
    return view


def mask_channels(channels: Any) -> dict[str, Any]:
    """Apply `public_view` across a whole bot.channels mapping."""
    if not isinstance(channels, dict):
        return {}
    return {name: public_view(name, cfg) for name, cfg in channels.items()}


def resolve_credentials(bot: dict, channel: str) -> dict[str, Any]:
    """
    Get the credentials to USE for a channel: per-bot config first, then the
    global .env as a fallback so pre-existing single-tenant setups keep working.
    """
    from app.config import get_settings

    channels = bot.get("channels") or {}
    cfg = channels.get(channel)
    if isinstance(cfg, dict) and cfg.get("connected"):
        # Per-bot values win, but fill any gaps from env.
        creds = {k: v for k, v in cfg.items() if k != "connected" and v}
        if creds:
            return creds

    s = get_settings()
    if channel == "whatsapp":
        return {
            "phone_number_id": s.whatsapp_phone_number_id,
            "access_token": s.whatsapp_token,
            "verify_token": s.whatsapp_verify_token,
        }
    if channel == "instagram":
        return {"access_token": s.instagram_token, "verify_token": s.instagram_verify_token}
    if channel == "slack":
        return {"bot_token": s.slack_bot_token, "signing_secret": s.slack_signing_secret}
    if channel == "email":
        return {
            "address": s.email_address,
            "app_password": s.email_password,
            "smtp_host": s.email_smtp_host,
            "smtp_port": str(s.email_smtp_port),
        }
    return {}


# ---------------------------------------------------------------------------
# Webhook → bot routing
# ---------------------------------------------------------------------------
# Incoming webhooks must find the bot that owns the account the message arrived
# on. Previously this was "first active bot with the flag set", which made it
# impossible to run two WhatsApp numbers. Now we match on the account identity
# carried in the payload, and only fall back to the old behaviour when nothing
# matches (keeps env-configured single-tenant setups working).


def _bots(active_only: bool = True) -> list[dict]:
    from app.database import get_supabase

    query = get_supabase().table("bots").select("*")
    if active_only:
        query = query.eq("is_active", True)
    return query.execute().data or []


def find_bot_by_field(
    channel: str, field: str, value: str, active_only: bool = True
) -> dict | None:
    """
    Find the bot whose `channels[channel][field]` equals `value`.

    `active_only=False` is used for the webhook verification handshake, which
    happens while the bot is still a draft — the user configures the provider
    before flipping the bot live. Message delivery keeps active_only=True so a
    paused bot stops answering.
    """
    if not value:
        return None
    for bot in _bots(active_only):
        cfg = (bot.get("channels") or {}).get(channel)
        if isinstance(cfg, dict) and cfg.get("connected") and str(cfg.get(field, "")) == str(value):
            return bot
    return None


def find_bot_for_channel(channel: str) -> dict | None:
    """Fallback: the first active bot with this channel connected at all."""
    for bot in _bots(active_only=True):
        cfg = (bot.get("channels") or {}).get(channel)
        if isinstance(cfg, dict):
            if cfg.get("connected"):
                return bot
        elif cfg:  # legacy truthy flag
            return bot
    return None


def verify_token_matches(channel: str, token: str) -> bool:
    """
    True if `token` matches ANY connected bot's verify token for this channel,
    or the global env value. Used by the Meta webhook GET handshake.
    """
    if not token:
        return False
    # active_only=False: the provider's handshake happens during setup, before
    # the owner activates the bot.
    if find_bot_by_field(channel, "verify_token", token, active_only=False):
        return True

    from app.config import get_settings

    s = get_settings()
    env_token = s.whatsapp_verify_token if channel == "whatsapp" else s.instagram_verify_token
    return bool(env_token) and token == env_token
