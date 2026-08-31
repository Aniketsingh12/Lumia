"""
Slack Channel Router
=====================

This router handles the Slack integration using Slack's Events API and
Interactive Components. It receives incoming Slack messages, processes them
through the AI engine, and sends responses back to the Slack channel.

Endpoints provided:
    POST /events    - Handle Slack event subscriptions (messages, URL verification)
    POST /interact  - Handle Slack interactive components (button clicks, etc.)

How Slack Integration Works (Setup):
    1. Create a Slack App at api.slack.com/apps.
    2. Enable "Event Subscriptions" and set the Request URL to our POST /events endpoint.
    3. Slack sends a URL verification challenge (type="url_verification") which we
       must respond to with the challenge value.
    4. Subscribe to "message" events in the Slack app configuration.
    5. Install the app to a Slack workspace.
    6. When a user sends a message in a channel where the bot is present,
       Slack sends a POST request to our /events endpoint.

Key Differences from WhatsApp/Instagram:
    - Slack uses its own Events API format (not Meta's webhook format).
    - URL verification is done via a POST request with a "challenge" field,
      not a GET request with query parameters.
    - We must ignore messages from bots (event.bot_id) to prevent infinite loops
      where our bot replies to its own messages.
    - Responses are sent to a Slack channel_id, not a user phone number.

Auth: These endpoints do NOT require JWT authentication because they are
called by Slack's servers, not by our users. Slack verifies requests using
signing secrets (not implemented here but recommended for production).
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.middleware.rate_limiter import check_bot_quota, check_rate_limit
from app.middleware.webhook_security import verify_slack_signature
from app.services import channel_registry as registry
from app.services.ai_engine import AIEngine
from app.services.channel_router import ChannelRouter
from app.services.conversation_manager import ConversationManager

# See whatsapp.py — the per-bot daily quota is the real ceiling on spend.
WEBHOOK_RATE_LIMIT = 120

# Create the router instance. Mounted with prefix like "/api/channels/slack".
router = APIRouter()

# Shared ChannelRouter for normalizing payloads and sending platform-specific responses
channel_router = ChannelRouter()


@router.post("/events")
async def handle_slack_events(request: Request):
    """
    Handle Slack event subscriptions (incoming messages and URL verification).

    HTTP Method: POST
    URL: /events
    Auth Required: No (called by Slack's servers)

    Request Body: JSON payload from Slack's Events API.
        The payload structure depends on the event type:

        URL Verification (sent once during setup):
        {
            "type": "url_verification",
            "challenge": "random_challenge_string",
            "token": "verification_token"
        }

        Message Event (sent when a user posts a message):
        {
            "type": "event_callback",
            "event": {
                "type": "message",
                "text": "Hello bot",
                "user": "U12345",
                "channel": "C12345",
                "bot_id": null  // present if message is from a bot
            }
        }

    Request Flow:
        1. Parse the JSON payload.
        2. Check if this is a URL verification challenge:
           - Slack sends this once when you first configure the webhook URL.
           - We respond with {"challenge": "<value>"} to prove we own the URL.
           - This is returned as a JSONResponse to ensure proper content-type.
        3. If it is a regular event, extract the "event" object.
        4. Ignore non-message events (e.g., channel_join, reaction_added).
        5. IMPORTANT: Ignore messages that have a "bot_id" field. This prevents
           infinite loops where our bot responds to its own messages, which would
           trigger another event, causing another response, and so on forever.
        6. Normalize the Slack payload into our standard message format using
           ChannelRouter.normalize_slack().
        7. Find a bot that has Slack configured as a channel:
           - Query all active bots
           - Check each bot's "channels" JSON for a "slack" key
           - Use the first matching bot
        8. Process the message through the standard AI pipeline:
           a. Get or create a conversation for this Slack user
           b. Save the customer's message
           c. Load conversation history
           d. Generate AI response
        9. Handle handoff if needed (fallback message + escalation).
        10. Save the AI response to the conversation.
        11. Send the response back to the Slack channel using
            ChannelRouter.send_slack(channel_id, text).

    Response:
        - URL verification: {"challenge": "<value>"}
        - Ignored events: {"status": "ignored"}
        - Successful processing: {"status": "ok"}
        - No bot configured: {"status": "no bot configured"}
    """
    # Raw bytes first — Slack's HMAC covers the exact body as sent.
    raw_body = await request.body()
    payload = await request.json()

    # URL verification challenge -- Slack sends this during initial webhook setup.
    # We must echo back the challenge value to prove we own this URL.
    if payload.get("type") == "url_verification":
        return JSONResponse(content={"challenge": payload["challenge"]})

    # Process event -- extract the event data from the payload
    event = payload.get("event", {})

    # Only handle "message" type events, and ignore messages from bots.
    # Ignoring bot messages prevents infinite loops (our bot replying to itself).
    if event.get("type") != "message" or event.get("bot_id"):
        return {"status": "ignored"}

    # Normalize Slack's payload into our standard internal message format
    message = channel_router.normalize_slack(payload)
    if not message:
        return {"status": "no message"}

    # Route to the bot connected to this Slack workspace (team_id), so multiple
    # workspaces can each have their own bot. Falls back to the first Slack bot
    # when no workspace ID was configured.
    team_id = payload.get("team_id", "")
    bot = registry.find_bot_by_field("slack", "team_id", team_id)
    if not bot and not team_id:
        # team_id is optional in the connect form, so an absent one is a legitimate
        # single-workspace setup. One that was sent but matched nothing is not, and
        # falling back there would let a forged payload choose a bot to bill.
        bot = registry.find_bot_for_channel("slack")
    if not bot:
        return {"status": "no bot configured"}

    creds = registry.resolve_credentials(bot, "slack")

    # Slack's signing secret is already a required field on connect, so unlike
    # Meta this is verifiable for every properly-configured bot.
    if not verify_slack_signature(
        raw_body,
        request.headers.get("X-Slack-Signature"),
        request.headers.get("X-Slack-Request-Timestamp"),
        creds.get("signing_secret"),
    ):
        raise HTTPException(status_code=403, detail="Invalid signature")

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
        channel="slack",
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

    # Save the AI response
    await conv_manager.add_message(
        conversation_id=conversation["id"],
        role="ai",
        content=response_text,
    )

    # Send the response back to the Slack channel where the message was received
    channel_id = event.get("channel", "")
    await channel_router.send_slack(channel_id, response_text, creds)

    return {"status": "ok"}


@router.post("/interact")
async def handle_slack_interactions(request: Request):
    """
    Handle Slack interactive components (buttons, menus, modals, etc.).

    HTTP Method: POST
    URL: /interact
    Auth Required: No (called by Slack's servers when a user clicks a button, etc.)

    Request Body: JSON payload from Slack's Interactivity webhook.
        Contains details about which interactive component was triggered
        and by whom.

    Request Flow:
        1. Parse the JSON payload.
        2. Handle interactive component actions (e.g., button clicks from
           handoff notification messages sent to agents in Slack).
        3. Currently a placeholder -- returns {"status": "ok"} for all interactions.

    Future Use Cases:
        - "Accept Handoff" button: When a conversation is escalated, a Slack
          message with a button is sent to the agent channel. Clicking it would
          assign the agent to the conversation.
        - "Quick Reply" buttons: Pre-defined response options for common questions.
        - Modal forms: More complex interactions like filling out customer details.

    Response: {"status": "ok"}
    """
    payload = await request.json()
    # Handle button clicks from handoff notifications
    return {"status": "ok"}
