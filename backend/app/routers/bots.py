"""
Bots Router
============

This router handles all CRUD (Create, Read, Update, Delete) operations for chatbots.
Bots are the core entity in BotForge -- each bot has its own personality, knowledge base,
channels, and configuration.

Endpoints provided:
    GET    /            - List all bots belonging to the current user's organization
    POST   /            - Create a new bot
    GET    /{bot_id}    - Get a specific bot's details
    PUT    /{bot_id}    - Update a bot's configuration
    DELETE /{bot_id}    - Delete a bot permanently
    PATCH  /{bot_id}/toggle - Toggle a bot's active/inactive status

All endpoints require authentication. Bots are scoped to the user's organization
(org_id), so users can only see and manage bots that belong to their own org.
This is enforced by filtering database queries with the user's org_id.

Design Decisions:
    - Bot IDs are generated server-side as UUIDs for uniqueness.
    - New bots start as inactive (is_active=False) and with zero message/doc counts.
    - The "channels" field is a JSON object that stores which messaging platforms
      (WhatsApp, Slack, Instagram, etc.) are connected to this bot.
    - Ownership verification is done by querying with both bot_id AND org_id,
      so a user from one org cannot access another org's bots.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from app.database import get_supabase
from app.models.bot import (
    BotCreate,
    BotUpdate,
    BotResponse,
    PromptGenRequest,
    PromptGenResponse,
)
from app.middleware.auth import get_current_user
from app.services.bot_genres import BOT_GENRES, DEFAULT_GENRE, get_genre
from app.services.channel_registry import mask_channels
from app.services.llm_client import LLMClient


def _safe(bot: dict) -> dict:
    """
    Strip channel secrets before a bot row leaves the API.

    bot.channels stores live access tokens, so every response path must go
    through here to keep them out of the browser. Returns a shallow copy with a
    freshly masked channels mapping, so the stored row (which the dev in-memory
    DB hands back by reference) is never mutated.
    """
    out = dict(bot)
    out["channels"] = mask_channels(bot.get("channels") or {})
    return out

# Create the router instance. Mounted with prefix like "/api/bots".
router = APIRouter()


@router.get("/", response_model=list[BotResponse])
async def list_bots(current_user: dict = Depends(get_current_user)):
    """
    List all bots for the current user's organization.

    HTTP Method: GET
    URL: /
    Auth Required: Yes

    Request Flow:
        1. The authenticated user's org_id is extracted from the JWT (via get_current_user).
        2. Query the "bots" table for all rows where org_id matches.
        3. Return the list of bots (may be empty if no bots exist yet).

    Response: List of BotResponse objects, each containing:
        - id, name, tone, greeting_message, fallback_message, custom_rules
        - avatar_url, channels, is_active, message_count, doc_count
        - created_at, updated_at
    """
    db = get_supabase()
    result = db.table("bots").select("*").eq("org_id", current_user["org_id"]).execute()
    return [_safe(b) for b in (result.data or [])]


@router.post("/", response_model=BotResponse)
async def create_bot(bot: BotCreate, current_user: dict = Depends(get_current_user)):
    """
    Create a new chatbot.

    HTTP Method: POST
    URL: /
    Auth Required: Yes

    Request Body (BotCreate):
        - name (str): Display name for the bot (e.g., "Customer Support Bot")
        - tone (str): Personality tone (e.g., "friendly", "professional", "casual")
        - greeting_message (str): First message shown when a conversation starts
        - fallback_message (str): Message sent when the bot cannot answer or escalates
        - custom_rules (str, optional): Additional behavior rules for the AI engine
        - avatar_url (str, optional): URL to the bot's profile picture

    Request Flow:
        1. Generate a new UUID for the bot.
        2. Build the bot data dict with the user's org_id, provided fields, and defaults:
           - channels: empty dict (no channels connected yet)
           - is_active: False (bot starts inactive, user must activate it)
           - message_count / doc_count: 0
           - timestamps set to current UTC time
        3. Insert the record into the "bots" table.
        4. Return the newly created bot data.

    Response: BotResponse with all bot fields including the generated ID.
    """
    db = get_supabase()
    bot_data = {
        "id": str(uuid.uuid4()),
        "org_id": current_user["org_id"],
        "name": bot.name,
        # Unknown genres silently fall back to support rather than erroring,
        # so an out-of-date frontend can never brick bot creation.
        "bot_type": bot.bot_type if bot.bot_type in BOT_GENRES else DEFAULT_GENRE,
        "persona": bot.persona,
        "tone": bot.tone,
        "greeting_message": bot.greeting_message,
        "fallback_message": bot.fallback_message,
        "custom_rules": bot.custom_rules,
        "system_prompt_override": bot.system_prompt_override,
        "avatar_url": bot.avatar_url,
        "channels": {},
        "is_active": False,
        "message_count": 0,
        "doc_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = db.table("bots").insert(bot_data).execute()
    return _safe(result.data[0])


@router.post("/generate-prompt", response_model=PromptGenResponse)
async def generate_prompt(
    req: PromptGenRequest, current_user: dict = Depends(get_current_user)
):
    """
    Generate a ready-to-use system prompt from a plain-language description.

    HTTP Method: POST
    URL: /generate-prompt
    Auth Required: Yes

    Why: writing a good system prompt is a skill. This lets a user describe
    what they want ("a friendly support bot for my bakery that helps with
    orders and never discusses refunds over $50") and get back a structured
    prompt they can drop into the bot's custom-prompt field and tweak.

    The request's genre/name/tone are folded into the meta-prompt so the
    generated text fits the bot being built. The LLM used is whatever provider
    is configured (Ollama/Claude/OpenAI).

    Response (PromptGenResponse):
        - prompt (str): The generated system prompt text.
    """
    description = (req.description or "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="Please describe what the bot should do.")

    genre = get_genre(req.bot_type)
    role = genre["role"] or "conversational character"
    name = (req.name or "the assistant").strip()
    tone = (req.tone or "friendly").strip()

    # Meta-prompt: instruct the LLM to act as a prompt engineer and return ONLY
    # the finished system prompt (no preamble, no markdown fences).
    meta_system = (
        "You are an expert prompt engineer. You write clear, effective system "
        "prompts for customer-facing AI chatbots. Given a short description, you "
        "produce a single polished system prompt.\n\n"
        "Rules for your output:\n"
        "- Write the prompt in the second person ('You are ...').\n"
        "- Include the bot's role, personality, what it should do, and a few clear "
        "behavioral rules or boundaries.\n"
        "- Keep it concise (roughly 80-160 words).\n"
        "- Do NOT include knowledge-base placeholders, confidence tags, or "
        "conversation-history sections — those are added automatically.\n"
        "- Output ONLY the system prompt text. No preamble, no explanation, no "
        "markdown code fences."
    )
    user_msg = (
        f"Bot name: {name}\n"
        f"Genre: {genre['label']} (behaves as a {role})\n"
        f"Tone: {tone}\n"
        f"Description of what it should do:\n{description}\n\n"
        "Write the system prompt now."
    )

    llm = LLMClient()
    try:
        generated = await llm.chat(
            system_prompt=meta_system,
            messages=[{"role": "user", "content": user_msg}],
            temperature=0.7,   # a little creativity for varied phrasing
            max_tokens=400,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Prompt generator is unavailable ({type(exc).__name__}). "
                   "Check that your LLM provider is running.",
        ) from exc

    # Strip stray markdown fences the model may add despite instructions.
    cleaned = generated.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        # drop a leading language hint like "text\n"
        if "\n" in cleaned:
            first, rest = cleaned.split("\n", 1)
            if len(first) < 12 and " " not in first.strip():
                cleaned = rest
    return PromptGenResponse(prompt=cleaned.strip())


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get a specific bot's details by ID.

    HTTP Method: GET
    URL: /{bot_id}
    Auth Required: Yes

    Path Parameters:
        - bot_id (str): The UUID of the bot to retrieve

    Request Flow:
        1. Query the "bots" table filtering by both bot_id AND the user's org_id.
           This ensures users can only access their own organization's bots.
        2. If no matching bot is found, return HTTP 404 "Bot not found".
        3. Otherwise, return the bot data.

    Response: BotResponse with all bot fields.

    Error Responses:
        - 404: Bot not found (either it does not exist or belongs to another org)
    """
    db = get_supabase()
    result = db.table("bots").select("*").eq("id", bot_id).eq("org_id", current_user["org_id"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Bot not found")
    return _safe(result.data[0])


@router.put("/{bot_id}", response_model=BotResponse)
async def update_bot(bot_id: str, bot: BotUpdate, current_user: dict = Depends(get_current_user)):
    """
    Update a bot's configuration.

    HTTP Method: PUT
    URL: /{bot_id}
    Auth Required: Yes

    Path Parameters:
        - bot_id (str): The UUID of the bot to update

    Request Body (BotUpdate):
        All fields are optional; only provided fields will be updated:
        - name, tone, greeting_message, fallback_message, custom_rules
        - avatar_url, channels, is_active

    Request Flow:
        1. Verify the bot exists and belongs to the user's org (ownership check).
           If not found, return HTTP 404.
        2. Extract only the non-None fields from the update request using model_dump(exclude_none=True).
           This means the client only needs to send the fields they want to change.
        3. Set the updated_at timestamp to the current UTC time.
        4. Apply the update to the database and return the updated bot.

    Response: BotResponse with the updated bot fields.

    Error Responses:
        - 404: Bot not found
    """
    db = get_supabase()

    # Verify ownership - query by both bot_id and org_id
    existing = db.table("bots").select("id").eq("id", bot_id).eq("org_id", current_user["org_id"]).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Bot not found")

    # Build update payload with only the fields that were provided (non-None)
    update_data = bot.model_dump(exclude_none=True)
    if "bot_type" in update_data and update_data["bot_type"] not in BOT_GENRES:
        update_data["bot_type"] = DEFAULT_GENRE
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = db.table("bots").update(update_data).eq("id", bot_id).execute()
    return _safe(result.data[0])


@router.delete("/{bot_id}")
async def delete_bot(bot_id: str, current_user: dict = Depends(get_current_user)):
    """
    Permanently delete a bot.

    HTTP Method: DELETE
    URL: /{bot_id}
    Auth Required: Yes

    Path Parameters:
        - bot_id (str): The UUID of the bot to delete

    Request Flow:
        1. Verify the bot exists and belongs to the user's org.
           If not found, return HTTP 404.
        2. Delete the bot record from the "bots" table.
        3. Return a confirmation message.

    Note: This does NOT cascade-delete related records (conversations, messages,
    knowledge docs, etc.). Those would need to be cleaned up separately or via
    database-level cascade rules.

    Response: {"message": "Bot deleted"}

    Error Responses:
        - 404: Bot not found
    """
    db = get_supabase()
    existing = db.table("bots").select("id").eq("id", bot_id).eq("org_id", current_user["org_id"]).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Bot not found")

    db.table("bots").delete().eq("id", bot_id).execute()
    return {"message": "Bot deleted"}


@router.patch("/{bot_id}/toggle", response_model=BotResponse)
async def toggle_bot(bot_id: str, current_user: dict = Depends(get_current_user)):
    """
    Toggle a bot's active/inactive status.

    HTTP Method: PATCH
    URL: /{bot_id}/toggle
    Auth Required: Yes

    Path Parameters:
        - bot_id (str): The UUID of the bot to toggle

    Request Flow:
        1. Fetch the bot (with full data since we need the current is_active value).
        2. If the bot is not found or belongs to another org, return HTTP 404.
        3. Flip the is_active boolean: if it was True, set to False, and vice versa.
        4. Update the bot record in the database with the new status and timestamp.
        5. Return the updated bot.

    Why PATCH instead of PUT:
        PATCH is used because we are modifying a single field (is_active) rather
        than replacing the entire bot resource. This follows REST conventions.

    Response: BotResponse with the updated is_active status.

    Error Responses:
        - 404: Bot not found
    """
    db = get_supabase()
    existing = db.table("bots").select("*").eq("id", bot_id).eq("org_id", current_user["org_id"]).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Bot not found")

    # Flip the active status
    new_status = not existing.data[0].get("is_active", False)
    result = db.table("bots").update({
        "is_active": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", bot_id).execute()
    return _safe(result.data[0])
