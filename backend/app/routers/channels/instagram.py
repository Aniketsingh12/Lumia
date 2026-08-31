"""
Instagram Channel Router
=========================

This router handles the Instagram Direct Messages (DM) integration via Meta's
Graph API. It receives incoming Instagram DMs via webhook, processes them through
the AI engine, and sends responses back to the customer.

Endpoints provided:
    GET  /webhook  - Webhook verification (required by Meta during initial setup)
    POST /webhook  - Receive incoming Instagram DMs and send AI responses

How Instagram Integration Works:
    Instagram uses the same Meta webhook infrastructure as WhatsApp. The setup
    process is nearly identical:
    1. Create a Facebook/Instagram App on the Meta Developer Portal.
    2. Configure the webhook URL pointing to our POST /webhook endpoint.
    3. Meta verifies the webhook via a GET request with a challenge.
    4. Once verified, Meta sends POST requests for every incoming Instagram DM.

    The key difference from WhatsApp:
    - Instagram uses a different verify_token setting (instagram_verify_token).
    - The payload structure is slightly different (Instagram Messaging API format).
    - Response is sent via ChannelRouter.send_instagram() instead of send_whatsapp().
    - Voice message transcription is not handled (Instagram DMs are typically text).

Auth: These endpoints do NOT require JWT authentication because they are
called by Meta's servers, not by our users.
"""

from fastapi import APIRouter, HTTPException, Query, Request

from app.middleware.rate_limiter import check_bot_quota, check_rate_limit
from app.middleware.webhook_security import verify_meta_signature
from app.services import channel_registry as registry
from app.services.ai_engine import AIEngine
from app.services.channel_router import ChannelRouter
from app.services.conversation_manager import ConversationManager

# See whatsapp.py for why this is generous — the per-bot daily quota is the
# real spend ceiling; this only blunts a flood from one source.
WEBHOOK_RATE_LIMIT = 120

# Create the router instance. Mounted with prefix like "/api/channels/instagram".
router = APIRouter()

# Shared ChannelRouter for normalizing payloads and sending platform-specific responses
channel_router = ChannelRouter()


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Meta webhook verification for Instagram.

    HTTP Method: GET
    URL: /webhook?hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=<challenge>
    Auth Required: No (called by Meta's servers during webhook setup)

    This works identically to the WhatsApp webhook verification (see whatsapp.py
    for a detailed explanation), except it uses the instagram_verify_token setting
    instead of whatsapp_verify_token.

    Query Parameters (using aliases because Meta uses dots in parameter names):
        - hub.mode (str): Should be "subscribe"
        - hub.verify_token (str): The shared secret configured in Meta's portal
        - hub.challenge (str): The challenge string to echo back

    Response: The challenge value as an integer (on success)

    Error Responses:
        - 403: Verification failed (token mismatch)
    """
    # Match any connected bot's per-bot verify token (or the global .env value).
    if hub_mode == "subscribe" and registry.verify_token_matches("instagram", hub_verify_token):
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_message(request: Request):
    """
    Handle incoming Instagram Direct Messages.

    HTTP Method: POST
    URL: /webhook
    Auth Required: No (called by Meta's servers when a customer sends a DM)

    Request Body: Raw JSON payload from Meta's Instagram Messaging API.
        The payload structure follows Meta's standard webhook format, similar
        to WhatsApp but with Instagram-specific fields.

    Request Flow:
        1. Parse the raw JSON payload from Meta.
        2. Normalize the payload using ChannelRouter.normalize_instagram() which
           extracts the sender's Instagram ID, message text, etc. into our
           standard internal message format.
        3. If no message is found (e.g., the event was a "seen" receipt or
           typing indicator, not an actual message), return {"status": "no message"}.
        4. Find a bot that has Instagram configured as a channel:
           - Query all active bots
           - Check each bot's "channels" JSON field for an "instagram" key
           - Use the first matching bot
        5. If no bot is configured for Instagram, return {"status": "no bot configured"}.
        6. Process the message through the standard AI pipeline:
           a. Get or create a conversation for this customer (using Instagram user ID)
           b. Save the customer's message
           c. Load conversation history for AI context
           d. Generate AI response via the AI engine (RAG search + LLM)
        7. Handle handoff: if AI confidence is too low, use the fallback message
           and escalate to a human agent.
        8. Save the AI response to the conversation.
        9. Send the response back to the customer via the Instagram Messaging API
           using ChannelRouter.send_instagram().

    Response: {"status": "ok"} on success, or {"status": "no message"/"no bot configured"}
    """
    # Raw bytes first — Meta's HMAC is over the exact body as sent.
    raw_body = await request.body()
    payload = await request.json()

    # Normalize Meta's Instagram payload into our standard message format
    message = channel_router.normalize_instagram(payload)
    if not message:
        return {"status": "no message"}

    # Route to the bot that owns the Instagram account this DM arrived on.
    # For IG messaging webhooks entry[].id is the business account's IG user ID.
    ig_user_id = ""
    try:
        ig_user_id = str(payload["entry"][0]["id"])
    except (KeyError, IndexError, TypeError):
        pass

    bot = registry.find_bot_by_field("instagram", "ig_user_id", ig_user_id)
    if not bot and not ig_user_id:
        # Fall back only when Meta sent no account id at all. An id that was sent
        # but matched nothing is a misconfiguration or a forgery, and falling back
        # would let an attacker pick an arbitrary bot to bill inference against.
        bot = registry.find_bot_for_channel("instagram")
    if not bot:
        return {"status": "no bot configured"}

    creds = registry.resolve_credentials(bot, "instagram")

    # Prove the request came from Meta before spending anything on it.
    if not verify_meta_signature(
        raw_body, request.headers.get("X-Hub-Signature-256"), creds.get("app_secret")
    ):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Defence in depth — and the only protection when no app secret is stored.
    await check_rate_limit(
        request.client.host if request.client else "unknown",
        scope="webhook",
        limit=WEBHOOK_RATE_LIMIT,
    )
    await check_bot_quota(bot["id"])

    # Process through the standard AI pipeline
    conv_manager = ConversationManager()
    conversation = await conv_manager.get_or_create(
        bot_id=bot["id"],
        channel="instagram",
        customer_id=message.sender_id,
    )

    # Save the customer's message
    await conv_manager.add_message(
        conversation_id=conversation["id"],
        role="customer",
        content=message.text,
    )

    # Load conversation history and generate AI response
    history = await conv_manager.get_history(conversation["id"])
    ai_engine = AIEngine()
    result = await ai_engine.process_message(
        bot_id=bot["id"],
        message=message.text,
        conversation_history=history,
        bot_config=bot,
    )

    # Determine response: fallback message if handoff, otherwise AI answer
    response_text = result["answer"]
    if result["handoff"]:
        response_text = bot.get("fallback_message", "Let me connect you to a human.")
        await conv_manager.escalate(conversation["id"])

    # Save the AI response to the conversation
    await conv_manager.add_message(
        conversation_id=conversation["id"],
        role="ai",
        content=response_text,
        meta={"confidence_score": result["confidence"], "intent": result["intent"]},
    )

    # Send the response back to the customer via Instagram Messaging API
    await channel_router.send_instagram(message.sender_id, response_text, creds)
    return {"status": "ok"}
