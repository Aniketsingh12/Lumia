"""
Channel Router Service
=======================

This module handles the translation between platform-specific message formats
and BotForge's internal unified format. It serves two purposes:

1. **Inbound normalization**: Each messaging platform (WhatsApp, Instagram, Slack)
   sends webhooks with completely different JSON structures. This service parses
   each platform's format and converts it into a single `UnifiedMessage` object
   that the rest of the system can work with uniformly.

2. **Outbound delivery**: When the AI generates a response, this service sends
   it back through the correct platform's API. The caller just says "send this
   message to this channel" and the router handles the API details.

Why it exists:
- Without this service, every part of the codebase would need platform-specific
  code to handle WhatsApp vs Instagram vs Slack differences. The channel router
  isolates all that complexity in one place.
- Adding a new channel (e.g., Telegram, Facebook Messenger) only requires adding
  new normalize_* and send_* methods here -- nothing else changes.

How it fits in the architecture:
- **Webhook API routes** call the normalize_* methods to parse incoming payloads.
- **Chat processing logic** calls send_response() to deliver the AI's answer
  back to the customer on the correct platform.
- The **website chat** channel uses WebSockets instead, so it doesn't go through
  this router for sending (but could for future webhook integrations).

Supported channels:
- WhatsApp (via Meta WhatsApp Business API)
- Instagram (via Meta Graph API for Instagram DMs)
- Slack (via Slack Events API and Web API)
- Website (uses WebSocket, not this router -- handled separately)
"""

from dataclasses import dataclass

import httpx

from app.config import get_settings


@dataclass
class UnifiedMessage:
    """
    A platform-agnostic representation of an incoming customer message.

    No matter which channel a message comes from (WhatsApp, Instagram, Slack,
    etc.), it gets converted into this common format. This means the AI engine,
    conversation manager, and other services never need to know which platform
    the customer is using.

    Attributes:
        channel: Which platform this message came from ("whatsapp", "instagram",
                 "slack", or "website").
        sender_id: The platform-specific ID of the person who sent the message
                   (e.g., a phone number for WhatsApp, a user ID for Slack).
        sender_name: The customer's display name, if available (may be None).
        text: The text content of the message. For voice messages this will be
              "[Voice message]"; for images it will be the caption or "[Image]".
        voice_url: URL or media ID for a voice/audio attachment (None if no audio).
        image_url: URL or media ID for an image attachment (None if no image).
        media_url: URL for other media types (None if no other media).
        raw_payload: The original, unmodified webhook payload (kept for debugging
                     and for any platform-specific processing needed later).
    """
    channel: str
    sender_id: str
    sender_name: str | None
    text: str
    voice_url: str | None = None
    image_url: str | None = None
    media_url: str | None = None
    raw_payload: dict | None = None


class ChannelRouter:
    """
    Normalize messages from any channel and send responses back.

    This class has two types of methods:
    - normalize_*() methods: Parse incoming webhook payloads into UnifiedMessage.
    - send_*() methods: Send outgoing messages via platform APIs.

    The send_response() method is the main outbound entry point -- it routes
    to the correct platform-specific send method based on the channel name.
    """

    # =========================================================================
    # INBOUND: Normalize incoming messages into UnifiedMessage
    # =========================================================================

    def normalize_whatsapp(self, payload: dict) -> UnifiedMessage | None:
        """
        Parse a Meta WhatsApp Business API webhook payload into a UnifiedMessage.

        WhatsApp webhook payloads have a deeply nested structure:
        payload -> entry[] -> changes[] -> value -> messages[]

        This method navigates that structure to extract the sender info,
        message type (text, audio, image), and content. It handles three
        message types:
        - text: Extracts the body text directly.
        - audio: Stores the media ID in voice_url (will be downloaded and
                 transcribed later by voice_processor).
        - image: Stores the media ID in image_url and uses the caption as text.

        Args:
            payload: The raw JSON body from the WhatsApp webhook.

        Returns:
            A UnifiedMessage if a valid message was found, or None if the
            payload is a status update or other non-message event.
        """
        try:
            # Navigate WhatsApp's nested webhook structure
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            # If there are no messages, this is a status update -- ignore it
            if not messages:
                return None

            msg = messages[0]  # Process the first message in the batch
            sender = msg.get("from", "")  # Sender's phone number
            msg_type = msg.get("type", "text")  # "text", "audio", "image", etc.

            text = ""
            voice_url = None
            image_url = None

            # Extract content based on message type
            if msg_type == "text":
                text = msg.get("text", {}).get("body", "")
            elif msg_type == "audio":
                # Store the media ID -- actual download happens in voice_processor
                voice_url = msg.get("audio", {}).get("id", "")
                text = "[Voice message]"  # Placeholder until transcription completes
            elif msg_type == "image":
                # Store the media ID -- actual download happens in image_processor
                image_url = msg.get("image", {}).get("id", "")
                text = msg.get("image", {}).get("caption", "[Image]")

            # Try to get the sender's display name from the contacts section
            contacts = value.get("contacts", [{}])
            sender_name = contacts[0].get("profile", {}).get("name") if contacts else None

            return UnifiedMessage(
                channel="whatsapp",
                sender_id=sender,
                sender_name=sender_name,
                text=text,
                voice_url=voice_url,
                image_url=image_url,
                raw_payload=payload,
            )
        except (IndexError, KeyError):
            # Malformed payload -- return None rather than crashing
            return None

    def normalize_instagram(self, payload: dict) -> UnifiedMessage | None:
        """
        Parse an Instagram DM webhook payload into a UnifiedMessage.

        Instagram DM webhooks use the Meta Graph API format:
        payload -> entry[] -> messaging[] -> message

        Simpler than WhatsApp, but supports text and media attachments.
        Media URLs are extracted from attachments if present.

        Args:
            payload: The raw JSON body from the Instagram webhook.

        Returns:
            A UnifiedMessage if a valid DM was found, or None on parse errors.
        """
        try:
            entry = payload.get("entry", [{}])[0]
            messaging = entry.get("messaging", [{}])[0]
            sender_id = messaging.get("sender", {}).get("id", "")
            message = messaging.get("message", {})

            text = message.get("text", "")

            # Check for media attachments (images, videos, etc.)
            media_url = None
            attachments = message.get("attachments", [])
            if attachments:
                media_url = attachments[0].get("payload", {}).get("url")

            return UnifiedMessage(
                channel="instagram",
                sender_id=sender_id,
                sender_name=None,  # Instagram DM webhooks don't include sender name
                text=text,
                media_url=media_url,
                raw_payload=payload,
            )
        except (IndexError, KeyError):
            return None

    def normalize_slack(self, payload: dict) -> UnifiedMessage | None:
        """
        Parse a Slack Events API payload into a UnifiedMessage.

        Slack event payloads are simpler: payload -> event -> {type, user, text}.
        We only process "message" events and ignore messages from bots (to avoid
        the bot responding to itself in an infinite loop).

        Args:
            payload: The raw JSON body from the Slack event subscription.

        Returns:
            A UnifiedMessage if this is a human user's message, or None if it's
            a bot message, a non-message event, or malformed.
        """
        event = payload.get("event", {})
        # Only handle "message" events, and ignore bot messages to prevent loops
        if event.get("type") != "message" or event.get("bot_id"):
            return None

        return UnifiedMessage(
            channel="slack",
            sender_id=event.get("user", ""),
            sender_name=None,  # Would need an extra API call to resolve the name
            text=event.get("text", ""),
            raw_payload=payload,
        )

    # =========================================================================
    # OUTBOUND: Send responses back to customers via platform APIs
    # =========================================================================

    async def send_whatsapp(
        self, recipient: str, message: str, creds: dict | None = None
    ) -> bool:
        """
        Send a text message to a WhatsApp user via the Meta WhatsApp Business API.

        Args:
            recipient: The recipient's phone number (in international format).
            message: The text message to send.
            creds: Per-bot credentials ({"phone_number_id", "access_token"}) from
                   the channel registry. Falls back to the global .env values so
                   older single-tenant deployments keep working.

        Returns:
            True if the message was sent successfully (HTTP 200), False otherwise.
        """
        settings = get_settings()
        creds = creds or {}
        phone_id = creds.get("phone_number_id") or settings.whatsapp_phone_number_id
        token = creds.get("access_token") or settings.whatsapp_token

        url = f"https://graph.facebook.com/{settings.graph_api_version}/{phone_id}/messages"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            return resp.status_code == 200

    async def send_instagram(
        self, recipient: str, message: str, creds: dict | None = None
    ) -> bool:
        """
        Send a text message to an Instagram user via the Meta Graph API.

        Args:
            recipient: The Instagram-scoped user ID to send to.
            message: The text message to send.
            creds: Per-bot credentials ({"access_token"}); falls back to .env.

        Returns:
            True if the message was sent successfully (HTTP 200), False otherwise.
        """
        settings = get_settings()
        creds = creds or {}
        token = creds.get("access_token") or settings.instagram_token

        url = f"https://graph.facebook.com/{settings.graph_api_version}/me/messages"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "recipient": {"id": recipient},
            "message": {"text": message},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            return resp.status_code == 200

    async def send_slack(
        self, channel_id: str, message: str, creds: dict | None = None
    ) -> bool:
        """
        Send a text message to a Slack channel via the Slack Web API.

        Args:
            channel_id: The Slack channel/DM/group ID to post in.
            message: The text message to send.
            creds: Per-bot credentials ({"bot_token"}); falls back to .env.

        Returns:
            True if the API call returned HTTP 200, False otherwise.
        """
        settings = get_settings()
        creds = creds or {}
        token = creds.get("bot_token") or settings.slack_bot_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {token}"},
                json={"channel": channel_id, "text": message},
            )
            return resp.status_code == 200

    # -------------------------------------------------------------------------
    # Unified outbound method
    # -------------------------------------------------------------------------

    async def send_response(
        self, channel: str, recipient: str, message: str, creds: dict | None = None
    ) -> bool:
        """
        Route an outgoing response to the correct platform-specific send method.

        This is the main outbound method that the rest of the application calls.
        It looks at the channel name and delegates to the appropriate send_*
        method. The caller doesn't need to know which platform the customer is on.

        Note: Website chat messages are delivered via WebSocket, not through this
        method. The WebSocket handling is in the chat API router.

        Args:
            channel: The platform name ("whatsapp", "instagram", "slack").
            recipient: The platform-specific recipient ID (phone number, user ID, etc.).
            message: The text message to send.

        Returns:
            True if the message was sent successfully, False if the channel is
            unknown or the API call failed.
        """
        if channel == "whatsapp":
            return await self.send_whatsapp(recipient, message, creds)
        elif channel == "instagram":
            return await self.send_instagram(recipient, message, creds)
        elif channel == "slack":
            return await self.send_slack(recipient, message, creds)
        # Website uses WebSocket, not this method
        return False
