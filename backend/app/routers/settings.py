"""
Settings Router
================

This router manages organization-level settings, team members, webhook
configurations, and API key management. These are administrative functions
used by organization owners and admins.

Endpoints provided:
    GET  /org        - Get the current organization's settings
    PUT  /org        - Update organization settings (name, plan)
    GET  /team       - List all team members in the organization
    POST /team       - Invite a new team member to the organization
    GET  /webhooks   - List all configured webhooks
    POST /webhooks   - Create a new webhook subscription
    GET  /api-keys   - List all API keys (metadata only, not the actual keys)
    POST /api-keys   - Generate a new API key

All endpoints require authentication.

Design Decisions:
    - Organization settings are scoped by the user's org_id (from their JWT),
      so users can only view/modify their own organization.
    - Team invitation creates a user record with an empty password_hash. The
      invited user would later set their password via an invite link (not yet
      implemented in this router).
    - Webhook subscriptions allow the platform to POST event notifications to
      external URLs when certain events occur (e.g., new message, escalation).
    - API keys are generated using Python's secrets module for cryptographic
      security. The full key is only returned once at creation time. Subsequent
      GET requests only return the key prefix for identification.
    - Note: The current implementation stores the raw API key in "key_hash".
      In production, this should be properly hashed (like a password) so that
      even a database breach does not expose the actual keys.
"""

import uuid
import secrets
from fastapi import APIRouter, Depends

from app.database import get_supabase
from app.middleware.auth import get_current_user

# Create the router instance. Mounted with prefix like "/api/settings".
router = APIRouter()


@router.get("/org")
async def get_org_settings(current_user: dict = Depends(get_current_user)):
    """
    Get the current organization's settings.

    HTTP Method: GET
    URL: /org
    Auth Required: Yes

    Request Flow:
        1. Extract the org_id from the authenticated user's profile.
        2. Query the "organizations" table for the matching record.
        3. Return the organization data (name, plan, owner_id, etc.).

    Response: Organization object with all fields, or empty dict if not found.
    """
    db = get_supabase()
    result = db.table("organizations").select("*").eq("id", current_user["org_id"]).execute()
    return result.data[0] if result.data else {}


@router.put("/org")
async def update_org_settings(data: dict, current_user: dict = Depends(get_current_user)):
    """
    Update the current organization's settings.

    HTTP Method: PUT
    URL: /org
    Auth Required: Yes

    Request Body (dict):
        Only whitelisted fields are accepted to prevent unauthorized changes:
        - name (str): The organization's display name
        - plan (str): The subscription plan (e.g., "free", "pro", "enterprise")

    Request Flow:
        1. Filter the incoming data to only include allowed fields ("name", "plan").
           This prevents clients from modifying sensitive fields like "owner_id".
        2. Update the organization record in the database.
        3. Return the updated organization data.

    Response: Updated organization object.
    """
    db = get_supabase()
    # Only allow updating specific fields to prevent unauthorized changes
    allowed_fields = {"name", "plan"}
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    result = db.table("organizations").update(update_data).eq("id", current_user["org_id"]).execute()
    return result.data[0] if result.data else {}


@router.get("/team")
async def get_team_members(current_user: dict = Depends(get_current_user)):
    """
    List all team members in the current organization.

    HTTP Method: GET
    URL: /team
    Auth Required: Yes

    Request Flow:
        1. Query the "users" table for all users in the same organization.
        2. Only select safe fields (id, email, full_name, role, avatar_url) --
           notably, password_hash is NOT included in the response.
        3. Return the list of team members.

    Response: List of user objects with: id, email, full_name, role, avatar_url.
    """
    db = get_supabase()
    result = db.table("users").select("id, email, full_name, role, avatar_url").eq("org_id", current_user["org_id"]).execute()
    return result.data or []


@router.post("/team")
async def invite_team_member(data: dict, current_user: dict = Depends(get_current_user)):
    """
    Invite a new team member to the organization.

    HTTP Method: POST
    URL: /team
    Auth Required: Yes

    Request Body (dict):
        - email (str, required): The email address of the person to invite
        - full_name (str, optional): The invitee's display name
        - role (str, optional): The role to assign. Defaults to "agent".
          Possible roles: "owner", "admin", "agent"

    Request Flow:
        1. Generate a new UUID for the user.
        2. Create a user record with the provided email, name, and role,
           linked to the current user's organization.
        3. Set password_hash to empty string -- the invited user will set
           their password later when they accept the invitation.
        4. Return the created user record.

    Note: This endpoint does NOT currently send an invitation email. The
    email notification and password-setting flow would need to be added
    for a complete invitation system.

    Response: The newly created user object.
    """
    db = get_supabase()
    member = {
        "id": str(uuid.uuid4()),
        "email": data["email"],
        "full_name": data.get("full_name", ""),
        "org_id": current_user["org_id"],
        "role": data.get("role", "agent"),
        "password_hash": "",  # Invited user sets password later
    }
    result = db.table("users").insert(member).execute()
    return result.data[0] if result.data else member


@router.get("/webhooks")
async def get_webhooks(current_user: dict = Depends(get_current_user)):
    """
    List all webhook configurations for the current organization.

    HTTP Method: GET
    URL: /webhooks
    Auth Required: Yes

    Request Flow:
        1. Query the "webhook_configs" table for all webhooks belonging to
           the current user's organization.
        2. Return the list (may be empty if no webhooks are configured).

    Webhooks allow external services to receive real-time notifications when
    events occur in BotForge (e.g., new message, conversation escalated).

    Response: List of webhook config objects with: id, org_id, url, events, is_active.
    """
    db = get_supabase()
    result = db.table("webhook_configs").select("*").eq("org_id", current_user["org_id"]).execute()
    return result.data or []


@router.post("/webhooks")
async def create_webhook(data: dict, current_user: dict = Depends(get_current_user)):
    """
    Create a new webhook subscription.

    HTTP Method: POST
    URL: /webhooks
    Auth Required: Yes

    Request Body (dict):
        - url (str, required): The URL to send webhook POST requests to
        - events (list[str], optional): Event types to subscribe to.
          Defaults to ["message.created", "conversation.escalated"].

    Request Flow:
        1. Generate a new UUID for the webhook.
        2. Create a webhook config record with the URL, subscribed events,
           and the current user's organization ID.
        3. The webhook starts as active (is_active=True).
        4. Return the created webhook config.

    When subscribed events occur, BotForge will send a POST request to the
    configured URL with a JSON payload containing the event data.

    Response: The newly created webhook config object.
    """
    db = get_supabase()
    webhook = {
        "id": str(uuid.uuid4()),
        "org_id": current_user["org_id"],
        "url": data["url"],
        "events": data.get("events", ["message.created", "conversation.escalated"]),
        "is_active": True,
    }
    result = db.table("webhook_configs").insert(webhook).execute()
    return result.data[0] if result.data else webhook


@router.get("/api-keys")
async def get_api_keys(current_user: dict = Depends(get_current_user)):
    """
    List all API keys for the current organization.

    HTTP Method: GET
    URL: /api-keys
    Auth Required: Yes

    Request Flow:
        1. Query the "api_keys" table for all keys belonging to the org.
        2. Only return metadata (id, name, prefix, created_at) -- the actual
           key value is NOT returned for security reasons.
        3. The "prefix" (first 8 characters) is shown so users can identify
           which key is which without exposing the full key.

    Response: List of API key metadata objects (without the actual key values).
    """
    db = get_supabase()
    result = db.table("api_keys").select("id, name, prefix, created_at").eq("org_id", current_user["org_id"]).execute()
    return result.data or []


@router.post("/api-keys")
async def create_api_key(data: dict, current_user: dict = Depends(get_current_user)):
    """
    Generate a new API key for the current organization.

    HTTP Method: POST
    URL: /api-keys
    Auth Required: Yes

    Request Body (dict):
        - name (str, optional): A label for the API key. Defaults to "Default".

    Request Flow:
        1. Generate a cryptographically secure random key using secrets.token_urlsafe(32).
           This produces a 43-character URL-safe base64 string.
        2. Store the key in the database along with the org_id, name, and prefix.
        3. Return the FULL key to the user. This is the ONLY time the full key
           is shown -- it cannot be retrieved later (only the prefix is stored
           for identification purposes).

    Security Note:
        The current implementation stores the raw key in "key_hash". In a production
        system, the key should be properly hashed (like bcrypt for passwords) before
        storage, so a database breach would not expose API keys.

    Response:
        - key (str): The full API key (shown only once)
        - name (str): The key's label
        - prefix (str): First 8 characters of the key (for identification)
    """
    db = get_supabase()
    # Generate a cryptographically secure random API key
    raw_key = secrets.token_urlsafe(32)
    key_data = {
        "id": str(uuid.uuid4()),
        "org_id": current_user["org_id"],
        "name": data.get("name", "Default"),
        "key_hash": raw_key,  # In production, hash this
        "prefix": raw_key[:8],
    }
    db.table("api_keys").insert(key_data).execute()
    # Return the full key -- this is the only time it will be visible
    return {"key": raw_key, "name": key_data["name"], "prefix": key_data["prefix"]}
