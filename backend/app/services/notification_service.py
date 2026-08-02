"""
Notification Service
=====================

This module sends alerts to human agents when a conversation needs their
attention. Currently, the primary trigger is escalation -- when the AI decides
it cannot handle a conversation (low confidence or sensitive intent), this
service notifies agents so they can jump in.

Why it exists:
- When the AI hands off a conversation, someone needs to know about it.
  Otherwise, the customer would be stuck waiting with no response.
- Notifications go to external channels (like Slack) where agents are already
  working, so they don't have to constantly watch the BotForge dashboard.

How it fits in the architecture:
- Called by the **chat processing logic** after ai_engine.should_handoff()
  returns True and the conversation has been escalated via conversation_manager.
- Currently supports **Slack notifications** (posts to a #support channel).
- Dashboard push notifications are handled separately via WebSocket in the
  chat API router (not in this module).

Future extensions:
- Email notifications
- SMS alerts
- Push notifications to a mobile app
- Configurable notification channels per bot/team
"""

import httpx
from app.config import get_settings


async def notify_escalation(conversation_id: str, bot_name: str, customer_name: str | None = None):
    """
    Send escalation notifications to agents via available channels.

    When a conversation is escalated to a human agent, this function sends
    a notification to alert the team. Currently it posts a rich Slack message
    to the #support channel with:
    - A clear header indicating a handoff is needed.
    - The customer's name and which bot they were talking to.
    - A "View Conversation" button linking directly to the conversation in
      the BotForge dashboard.

    The notification is sent on a best-effort basis -- if Slack is unavailable
    or not configured, the function silently continues (the dashboard's
    WebSocket-based notifications serve as a fallback).

    Data flow:
    1. Build a human-readable alert message.
    2. Check if a Slack bot token is configured.
    3. If yes, POST a message to Slack's chat.postMessage API with rich
       formatting (Block Kit blocks for the header and action button).
    4. Return True regardless (best-effort delivery).

    Args:
        conversation_id: The ID of the escalated conversation (used in the
                         dashboard link so agents can find it quickly).
        bot_name: The name of the bot that was handling the conversation
                  (helps agents understand the context).
        customer_name: The customer's name if available. Defaults to
                       "A customer" if not provided.

    Returns:
        True always (notifications are best-effort and should not block
        the main conversation flow even if they fail).
    """
    settings = get_settings()
    customer = customer_name or "A customer"
    message = f"🚨 {customer} needs human help with {bot_name}. Conversation: {conversation_id}"

    # --- Slack notification ---
    # Only attempt if a Slack bot token is configured in settings
    if settings.slack_bot_token:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
                    json={
                        "channel": "#support",  # Posts to the #support channel
                        "text": message,         # Fallback text for notifications
                        "blocks": [
                            # Rich formatted message using Slack Block Kit
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*🚨 Human Handoff Required*\n{customer} needs help.\nBot: {bot_name}",
                                },
                            },
                            # Action button that links to the conversation in the dashboard
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {"type": "plain_text", "text": "View Conversation"},
                                        "url": f"{settings.app_url}/conversations/{conversation_id}",
                                        "style": "primary",  # Blue button to draw attention
                                    }
                                ],
                            },
                        ],
                    },
                )
        except Exception:
            # Silently ignore Slack failures -- notifications are best-effort.
            # The dashboard WebSocket notifications serve as a backup.
            pass

    # Dashboard push notification via WebSocket is handled by the chat router,
    # not here. This function only handles external notification channels.
    return True
