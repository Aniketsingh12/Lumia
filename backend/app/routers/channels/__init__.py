"""
Channels Package
=================

This package contains routers for external messaging platform integrations.
Each module handles incoming webhook events from a specific platform and
sends responses back through that platform's API.

Supported Channels:
    - whatsapp.py  : WhatsApp Business API integration (via Meta/Facebook)
    - instagram.py : Instagram Direct Messages integration (via Meta/Facebook)
    - slack.py     : Slack workspace integration (via Slack Events API)
    - email.py     : Email integration (via SMTP for outbound replies)

How Channel Integrations Work:
    1. The external platform (WhatsApp, Instagram, Slack) is configured to send
       webhook events to our API endpoints when a new message arrives.
    2. Our webhook endpoint receives the raw payload from the platform.
    3. The ChannelRouter service normalizes the platform-specific payload into
       a standard internal message format (sender_id, sender_name, text, etc.).
    4. The normalized message is processed through the same AI pipeline as any
       other message: save to conversation, run through AI engine, generate response.
    5. The response is sent back to the customer through the platform's API
       (e.g., WhatsApp Cloud API, Instagram Graph API, Slack Web API).

Each platform has its own webhook verification mechanism:
    - Meta (WhatsApp/Instagram): GET request with hub.verify_token challenge
    - Slack: POST request with type="url_verification" and a challenge string
    - Email: No inbound webhook (email uses SMTP for outbound only)
"""
