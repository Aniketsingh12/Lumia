"""
Conversations Router
=====================

This router manages conversation lifecycle and agent interactions. While the chat
router handles the AI-to-customer messaging flow, this router provides the tools
that human agents use to monitor, manage, and participate in conversations.

Endpoints provided:
    GET    /                            - List conversations with optional filters
    GET    /{conversation_id}           - Get a conversation with all its messages
    PATCH  /{conversation_id}/assign    - Assign a human agent to a conversation
    PATCH  /{conversation_id}/resolve   - Mark a conversation as resolved
    PATCH  /{conversation_id}/handoff   - Manually escalate a conversation to a human agent
    POST   /{conversation_id}/reply     - Send a human agent's reply into a conversation
    GET    /{conversation_id}/suggest   - Get an AI-suggested reply for an agent to use

All endpoints require authentication.

Conversation Lifecycle:
    1. A conversation starts when a customer sends their first message (created in chat.py).
    2. The bot handles the conversation autonomously using AI.
    3. If the bot's confidence drops below a threshold, it escalates (handoff).
    4. A human agent is notified and can be assigned to the conversation.
    5. The agent can view the conversation, send replies, and use AI-suggested replies.
    6. Once the issue is resolved, the agent marks the conversation as "resolved".

Design Decisions:
    - Conversations can be filtered by bot_id, status, and channel for the agent dashboard.
    - Agent replies are broadcast via WebSocket so the customer sees them in real time.
    - The "suggest" endpoint generates an AI-powered draft reply that agents can edit
      before sending, improving response speed and consistency.
"""

from fastapi import APIRouter, HTTPException, Depends, Query

from app.database import get_supabase
from app.models.conversation import ConversationResponse, AgentReply
from app.services.conversation_manager import ConversationManager
from app.services.ai_engine import AIEngine
from app.middleware.auth import get_current_user
# Import the WebSocket manager from chat.py so agent replies can be broadcast in real time
from app.routers.chat import manager as ws_manager

# Create the router instance. Mounted with prefix like "/api/conversations".
router = APIRouter()


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    bot_id: str | None = Query(None),
    status: str | None = Query(None),
    channel: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """
    List conversations with optional filtering.

    HTTP Method: GET
    URL: /
    Auth Required: Yes

    Query Parameters (all optional):
        - bot_id (str): Filter by bot UUID -- show only conversations for this bot
        - status (str): Filter by status -- e.g., "active", "escalated", "resolved"
        - channel (str): Filter by channel -- e.g., "web", "whatsapp", "slack"

    Request Flow:
        1. Build a query on the "conversations" table, ordered by newest first.
        2. Apply any provided filters (bot_id, status, channel).
        3. Limit results to 100 conversations (to prevent large payloads).
        4. Return the list.

    This endpoint powers the agent dashboard's conversation list view, where agents
    can see all active, escalated, or resolved conversations and filter by bot/channel.

    Response: List of ConversationResponse objects, each containing:
        - id, bot_id, channel, customer_id, customer_name, status
        - started_at, last_message_at, assigned_agent_id, etc.
    """
    db = get_supabase()
    org_id = current_user["org_id"]

    # When bot_id is given, use it directly (bots.py already enforces org ownership).
    # Otherwise, scope to bots belonging to the current org by joining through the bot.
    if bot_id:
        query = (
            db.table("conversations")
            .select("*")
            .eq("bot_id", bot_id)
            .order("started_at", desc=True)
        )
    else:
        # Fetch the caller's bot IDs first, then filter conversations to those bots.
        org_bots = db.table("bots").select("id").eq("org_id", org_id).execute()
        bot_ids = [b["id"] for b in (org_bots.data or [])]
        if not bot_ids:
            return []
        # Supabase supports `.in_()` for multi-value filters; dev_db handles eq per-row.
        query = db.table("conversations").select("*").order("started_at", desc=True)
        # Filter in Python for dev-mode compat (Supabase `.in_()` is not in shim).
        result = query.limit(500).execute()
        filtered = [c for c in (result.data or []) if c.get("bot_id") in bot_ids]
        if status:
            filtered = [c for c in filtered if c.get("status") == status]
        if channel:
            filtered = [c for c in filtered if c.get("channel") == channel]
        return filtered[:100]

    if status:
        query = query.eq("status", status)
    if channel:
        query = query.eq("channel", channel)

    result = query.limit(100).execute()
    return result.data or []


@router.get("/{conversation_id}", response_model=dict)
async def get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get a single conversation with all its messages.

    HTTP Method: GET
    URL: /{conversation_id}
    Auth Required: Yes

    Path Parameters:
        - conversation_id (str): The UUID of the conversation to retrieve

    Request Flow:
        1. Fetch the conversation metadata from the "conversations" table.
           If not found, return HTTP 404.
        2. Fetch all messages for this conversation from the "messages" table,
           ordered chronologically (oldest first) so the chat history reads naturally.
        3. Return both the conversation metadata and the full message list.

    Response (dict):
        - conversation: The conversation metadata object
        - messages: List of all messages in chronological order, each with:
          role ("customer", "ai", or "agent"), content, timestamps, feedback, etc.

    Error Responses:
        - 404: Conversation not found
    """
    db = get_supabase()

    conv = db.table("conversations").select("*").eq("id", conversation_id).execute()
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Fetch messages ordered chronologically (oldest first)
    messages = (
        db.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )

    return {
        "conversation": conv.data[0],
        "messages": messages.data or [],
    }


@router.patch("/{conversation_id}/assign")
async def assign_conversation(
    conversation_id: str,
    agent_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Assign a human agent to a conversation.

    HTTP Method: PATCH
    URL: /{conversation_id}/assign?agent_id=<uuid>
    Auth Required: Yes

    Path Parameters:
        - conversation_id (str): The UUID of the conversation

    Query Parameters:
        - agent_id (str, required): The UUID of the agent to assign

    Request Flow:
        1. Call the ConversationManager to update the conversation's assigned_agent_id
           and change the status to indicate an agent is handling it.
        2. Return the updated conversation data.

    This is used when a team lead or the agent themselves claims an escalated conversation.

    Response: Updated conversation data from the ConversationManager.
    """
    conv_manager = ConversationManager()
    result = await conv_manager.assign_agent(conversation_id, agent_id)
    return result


@router.patch("/{conversation_id}/resolve")
async def resolve_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Mark a conversation as resolved.

    HTTP Method: PATCH
    URL: /{conversation_id}/resolve
    Auth Required: Yes

    Path Parameters:
        - conversation_id (str): The UUID of the conversation to resolve

    Request Flow:
        1. Call the ConversationManager to set the conversation status to "resolved"
           and record which user resolved it (current_user's ID).
        2. Return the updated conversation data.

    Once resolved, the conversation is considered closed. It will still appear in
    the conversation list when filtered by status="resolved" for historical reference.

    Response: Updated conversation data from the ConversationManager.
    """
    conv_manager = ConversationManager()
    result = await conv_manager.resolve(conversation_id, current_user.get("id"))
    return result


@router.patch("/{conversation_id}/handoff")
async def trigger_handoff(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Manually escalate a conversation to a human agent.

    HTTP Method: PATCH
    URL: /{conversation_id}/handoff
    Auth Required: Yes

    Path Parameters:
        - conversation_id (str): The UUID of the conversation to escalate

    Request Flow:
        1. Call the ConversationManager to mark the conversation as escalated.
           This changes the status to "escalated" and flags it for agent attention.
        2. Send a notification to the team (via the notification service) so agents
           know a conversation needs human attention.
        3. Return the updated conversation data.

    This is different from automatic escalation (which happens in chat.py when AI
    confidence is low). This endpoint allows an agent who is reviewing a conversation
    to manually decide it needs human intervention.

    Response: Updated conversation data from the ConversationManager.
    """
    conv_manager = ConversationManager()
    result = await conv_manager.escalate(conversation_id)

    # Notify the team about the manual escalation
    from app.services.notification_service import notify_escalation

    await notify_escalation(conversation_id, "Bot")
    return result


@router.post("/{conversation_id}/reply")
async def agent_reply(
    conversation_id: str,
    reply: AgentReply,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a human agent's reply into a conversation.

    HTTP Method: POST
    URL: /{conversation_id}/reply
    Auth Required: Yes

    Path Parameters:
        - conversation_id (str): The UUID of the conversation

    Request Body (AgentReply):
        - content (str): The text of the agent's reply

    Request Flow:
        1. Save the agent's message to the conversation with role="agent".
           This distinguishes it from AI messages (role="ai") and customer
           messages (role="customer") in the conversation history.
        2. Broadcast the message via WebSocket to all connected clients
           (including the customer's chat widget), so they see the agent's
           reply in real time without needing to refresh.
        3. Return the saved message data.

    Response: The saved message object (with id, conversation_id, role, content, etc.)
    """
    conv_manager = ConversationManager()
    message = await conv_manager.add_message(
        conversation_id=conversation_id,
        role="agent",
        content=reply.content,
    )

    # Broadcast via WebSocket so the customer and other agents see the reply instantly
    await ws_manager.broadcast(conversation_id, {
        "type": "new_message",
        "message": message,
    })

    return message


@router.get("/{conversation_id}/suggest")
async def get_suggested_reply(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get an AI-suggested reply for an agent to use or edit.

    HTTP Method: GET
    URL: /{conversation_id}/suggest
    Auth Required: Yes

    Path Parameters:
        - conversation_id (str): The UUID of the conversation

    Request Flow:
        1. Load the full conversation history.
        2. Look up the bot associated with this conversation.
           If the conversation does not exist, return HTTP 404.
        3. Load the bot's configuration (tone, rules, knowledge base context).
        4. Ask the AI engine to generate a suggested reply based on the
           conversation history and bot config.
        5. Return the suggestion as text that the agent can review, edit, and send.

    This feature helps agents respond faster and more consistently by providing
    AI-generated draft replies that align with the bot's tone and knowledge base.

    Response:
        - suggestion (str): AI-generated suggested reply text

    Error Responses:
        - 404: Conversation not found
    """
    conv_manager = ConversationManager()
    history = await conv_manager.get_history(conversation_id)

    db = get_supabase()
    conv = db.table("conversations").select("bot_id").eq("id", conversation_id).execute()
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    bot_id = conv.data[0]["bot_id"]
    bot_result = db.table("bots").select("*").eq("id", bot_id).execute()
    bot_config = bot_result.data[0] if bot_result.data else {}

    ai_engine = AIEngine()
    suggestion = await ai_engine.get_suggested_reply(history, bot_config)
    return {"suggestion": suggestion}
