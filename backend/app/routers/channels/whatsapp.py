"""
WhatsApp Channel Router
========================

This router handles the WhatsApp Business API integration. It receives incoming
WhatsApp messages via webhook, processes them through the AI engine, and sends
responses back to the customer via the WhatsApp Cloud API.

Endpoints provided:
    GET  /webhook  - Webhook verification (required by Meta during initial setup)
    POST /webhook  - Receive incoming WhatsApp messages and send AI responses

How WhatsApp Integration Works (Setup):
    1. You create a WhatsApp Business App on the Meta Developer Portal.
    2. In the app settings, you configure a webhook URL pointing to our POST /webhook.
    3. Meta sends a GET request to verify the webhook URL (see verify_webhook below).
    4. Once verified, Meta will POST all incoming WhatsApp messages to our endpoint.

How Incoming Messages Are Processed:
    1. Meta sends a POST request with a JSON payload containing the message data.
       The payload structure is nested: entry[] -> changes[] -> value -> messages[].
    2. The ChannelRouter.normalize_whatsapp() method extracts the relevant fields
       (sender phone number, message text, etc.) from Meta's nested format.
    3. If the message is a voice message, it is transcribed to text first.
    4. We find the bot that has WhatsApp configured as a channel.
    5. The message is processed through the standard AI pipeline:
       - Get or create a conversation for this customer
       - Save the customer message
       - Load conversation history
       - Generate AI response via the AI engine (RAG + LLM)
       - If confidence is low, escalate to a human agent
    6. The AI response is sent back to the customer via the WhatsApp Cloud API
       using ChannelRouter.send_whatsapp().

Auth: These endpoints do NOT require our JWT authentication because they are
called by Meta's servers, not by our users. Meta verifies webhooks using a
shared verify_token configured in the Meta Developer Portal.
"""

from fastapi import APIRouter, HTTPException, Query, Request

from app.services import channel_registry as registry
from app.services.ai_engine import AIEngine
from app.services.channel_router import ChannelRouter
from app.services.conversation_manager import ConversationManager
from app.services.voice_processor import transcribe_whatsapp_media

# Create the router instance. Mounted with prefix like "/api/channels/whatsapp".
router = APIRouter()

# The ChannelRouter handles normalizing platform-specific payloads and sending
# responses back through each platform's API.
channel_router = ChannelRouter()


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Meta webhook verification endpoint.

    HTTP Method: GET
    URL: /webhook?hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=<challenge>
    Auth Required: No (called by Meta's servers during webhook setup)

    How Meta Webhook Verification Works:
        When you first configure the webhook URL in the Meta Developer Portal, Meta
        sends a GET request to verify that the URL is valid and owned by you. The
        request includes three query parameters:
            - hub.mode: Always "subscribe" for webhook verification
            - hub.verify_token: A secret token you configured in the Meta portal.
              Our server compares this against our stored whatsapp_verify_token.
            - hub.challenge: A random string from Meta that we must echo back.

        If the verify_token matches, we return the hub.challenge value as a plain
        integer (Meta requires this exact format). If it does not match, we return
        HTTP 403 to reject the verification.

    Query Parameters (using aliases because Meta uses dots in parameter names):
        - hub.mode (str): Should be "subscribe"
        - hub.verify_token (str): The shared secret to verify
        - hub.challenge (str): The challenge string to echo back

    Response: The challenge value as an integer (on success)

    Error Responses:
        - 403: Verification failed (token mismatch)
    """
    # Match against any connected bot's per-bot verify token (and the global
    # .env value as a fallback), since each bot now brings its own credentials.
    if hub_mode == "subscribe" and registry.verify_token_matches("whatsapp", hub_verify_token):
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_message(request: Request):
    """
    Handle incoming WhatsApp messages.

    HTTP Method: POST
    URL: /webhook
    Auth Required: No (called by Meta's servers when a customer sends a message)

    Request Body: Raw JSON payload from Meta's WhatsApp Cloud API.
        The payload has a deeply nested structure:
        {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "phone_number",
                            "text": {"body": "message text"},
                            "type": "text" | "audio" | ...
                        }],
                        "contacts": [{"profile": {"name": "Customer Name"}}]
                    }
                }]
            }]
        }

    Request Flow:
        1. Parse the raw JSON payload from Meta.
        2. Normalize the payload using ChannelRouter.normalize_whatsapp() which
           extracts the sender's phone number, name, message text, and any media URLs
           into a standard internal message format.
        3. If no message is found (e.g., it was a status update, not a message),
           return early with {"status": "no message"}.
        4. If the message contains a voice note (voice_url is set), transcribe it
           to text using the voice_processor service (speech-to-text).
        5. Find a bot that has WhatsApp configured as a channel:
           - Query all active bots
           - Check each bot's "channels" JSON field for a "whatsapp" key
           - Use the first matching bot
        6. If no bot is configured for WhatsApp, return {"status": "no bot configured"}.
        7. Process the message through the standard AI pipeline:
           a. Get or create a conversation for this customer (using phone number as ID)
           b. Save the customer's message to the conversation
           c. Load conversation history for AI context
           d. Send through the AI engine (RAG search + LLM response generation)
        8. Handle handoff: if the AI confidence is too low, use the bot's fallback
           message and escalate the conversation to a human agent.
        9. Save the AI (or fallback) response to the conversation.
        10. Send the response back to the customer via the WhatsApp Cloud API
            using ChannelRouter.send_whatsapp().

    Response: {"status": "ok"} on success, or {"status": "no message"/"no bot configured"}
    """
    payload = await request.json()

    # Normalize Meta's nested payload into our standard message format
    message = channel_router.normalize_whatsapp(payload)
    if not message:
        return {"status": "no message"}

    # Handle voice messages by transcribing audio to text
    if message.voice_url:
        message.text = await transcribe_whatsapp_media(message.voice_url)

    # Route to the bot that owns the WhatsApp number this message arrived on.
    # Meta puts the receiving number's ID in entry[].changes[].value.metadata,
    # so several bots can each run their own WhatsApp number. If nothing matches
    # (e.g. credentials still in .env), fall back to the first WhatsApp bot.
    phone_number_id = ""
    try:
        phone_number_id = (
            payload["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
        )
    except (KeyError, IndexError, TypeError):
        pass

    bot = registry.find_bot_by_field("whatsapp", "phone_number_id", phone_number_id)
    if not bot:
        bot = registry.find_bot_for_channel("whatsapp")
    if not bot:
        return {"status": "no bot configured"}

    creds = registry.resolve_credentials(bot, "whatsapp")

    # Process message through the standard AI pipeline
    conv_manager = ConversationManager()
    conversation = await conv_manager.get_or_create(
        bot_id=bot["id"],
        channel="whatsapp",
        customer_id=message.sender_id,
        customer_name=message.sender_name,
    )

    # Save the customer's incoming message
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

    # Determine the response: use fallback message if handoff is triggered
    response_text = result["answer"]
    if result["handoff"]:
        response_text = bot.get("fallback_message", "Let me connect you to a human.")
        await conv_manager.escalate(conversation["id"])

    # Save the AI/fallback response to the conversation
    await conv_manager.add_message(
        conversation_id=conversation["id"],
        role="ai",
        content=response_text,
        meta={"confidence_score": result["confidence"], "intent": result["intent"]},
    )

    # Send response back via WhatsApp Cloud API to the customer's phone number,
    # using this bot's own credentials.
    await channel_router.send_whatsapp(message.sender_id, response_text, creds)

    return {"status": "ok"}
