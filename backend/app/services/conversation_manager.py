"""
Conversation Manager Service
==============================

This module manages the lifecycle and state of conversations in the database.
A "conversation" in BotForge is the full interaction between a customer and a
bot (or human agent), including all the messages exchanged.

Why it exists:
- Every message needs to be stored so the AI can see conversation history and
  generate contextually appropriate responses.
- Conversations have states (active, escalated, resolved) that need to be
  tracked for analytics and agent dashboards.
- The system needs to know whether to resume an existing conversation or start
  a new one when a customer sends a message.

How it fits in the architecture:
- Called by **chat API routes** at the start of every incoming message to find
  (or create) the conversation, then again to store the customer's message
  and the AI's response.
- Called by **agent dashboard API routes** when a human agent escalates,
  resolves, or gets assigned to a conversation.
- The conversation history it provides is fed to **ai_engine.py** so the AI
  can maintain context across multiple messages.

Database: All data is stored in Supabase (a hosted PostgreSQL + REST API).
Tables used:
- "conversations": One row per conversation, tracking status, channel, etc.
- "messages": One row per message, linked to a conversation by conversation_id.
"""

import uuid
from datetime import datetime, timezone

from app.database import get_supabase


class ConversationManager:
    """
    Manage conversation state and message storage in Supabase.

    This class provides CRUD operations for conversations and messages.
    It handles the full lifecycle: creating conversations, adding messages,
    retrieving history, escalating to humans, and resolving.

    Attributes:
        db: The Supabase client used for all database operations.
    """

    def __init__(self):
        """Initialize with a Supabase database client."""
        self.db = get_supabase()

    # -------------------------------------------------------------------------
    # Conversation lifecycle
    # -------------------------------------------------------------------------

    async def get_or_create(
        self,
        bot_id: str,
        channel: str,
        customer_id: str | None = None,
        customer_name: str | None = None,
    ) -> dict:
        """
        Get an existing active conversation or create a new one.

        When a customer sends a message, we first check if they already have
        an active conversation with this bot on this channel. If so, we return
        it (to continue the conversation). If not, we create a new one.

        This ensures:
        - Repeat messages from the same customer continue in the same thread.
        - New customers get a fresh conversation.
        - If a previous conversation was resolved/escalated, a new one starts.

        Args:
            bot_id: The bot that should handle this conversation.
            channel: Which platform the message came from ("whatsapp", "slack", etc.).
            customer_id: The customer's platform-specific ID. If None, a random
                         UUID is generated (useful for anonymous website visitors).
            customer_name: The customer's display name (may be None).

        Returns:
            A dict representing the conversation row from Supabase, with fields
            like id, bot_id, channel, customer_id, status, started_at, etc.
        """
        # Try to find an active conversation for this customer on this channel
        if customer_id:
            result = (
                self.db.table("conversations")
                .select("*")
                .eq("bot_id", bot_id)
                .eq("channel", channel)
                .eq("customer_id", customer_id)
                .eq("status", "active")  # Only look for active conversations
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]  # Found an existing conversation -- reuse it

        # No active conversation found -- create a new one
        conversation = {
            "id": str(uuid.uuid4()),
            "bot_id": bot_id,
            "channel": channel,
            "customer_id": customer_id or str(uuid.uuid4()),  # Generate ID for anonymous users
            "customer_name": customer_name,
            "status": "active",        # New conversations start as "active"
            "ai_resolution": True,     # Assume AI will resolve it until proven otherwise
            "tags": [],                # Tags can be added later by agents
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        result = self.db.table("conversations").insert(conversation).execute()
        return result.data[0] if result.data else conversation

    # -------------------------------------------------------------------------
    # Message management
    # -------------------------------------------------------------------------

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        meta: dict | None = None,
    ) -> dict:
        """
        Add a message to a conversation and update the conversation's last_message.

        Every message exchanged (customer messages, AI responses, and agent
        messages) is stored in the "messages" table. This creates a complete
        audit trail and provides the conversation history that the AI needs
        for context.

        The message can include optional metadata:
        - source_chunks: Which knowledge base chunks were used (for AI messages).
        - confidence_score: How confident the AI was (for AI messages).
        - intent: The classified intent of the customer's message.
        - attachments: Any files/images attached to the message.

        Args:
            conversation_id: The conversation this message belongs to.
            role: Who sent this message -- "customer", "ai", or "agent".
            content: The text content of the message.
            meta: Optional dict with additional metadata (source_chunks,
                  confidence_score, intent, attachments).

        Returns:
            A dict representing the inserted message row from Supabase.
        """
        message = {
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": role,           # "customer", "ai", or "agent"
            "content": content,
            "source_chunks": (meta or {}).get("source_chunks", []),
            "confidence_score": (meta or {}).get("confidence_score"),
            "intent": (meta or {}).get("intent"),
            "attachments": (meta or {}).get("attachments", []),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = self.db.table("messages").insert(message).execute()

        # Update the conversation's last_message preview for the dashboard
        self.db.table("conversations").update({
            "last_message": content[:200],
        }).eq("id", conversation_id).execute()

        return result.data[0] if result.data else message

    async def get_history(self, conversation_id: str, limit: int = 10) -> list[dict]:
        """
        Get recent messages from a conversation, ordered oldest-first.

        This is used to build the conversation history that gets passed to the
        AI engine. The AI uses this context to understand what was already
        discussed and provide coherent follow-up answers.

        Args:
            conversation_id: The conversation to fetch messages for.
            limit: Maximum number of messages to return (default 10).
                   Older messages beyond this limit are excluded.

        Returns:
            A list of message dicts ordered by created_at ascending (oldest first),
            each containing role, content, and other fields.
        """
        result = (
            self.db.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)  # Oldest first, so conversation reads naturally
            .limit(limit)
            .execute()
        )
        return result.data or []

    # -------------------------------------------------------------------------
    # Conversation state transitions
    # -------------------------------------------------------------------------

    async def escalate(self, conversation_id: str) -> dict:
        """
        Escalate a conversation to a human agent.

        This is triggered when the AI decides it cannot confidently handle the
        conversation (see ai_engine.should_handoff()). The conversation status
        changes from "active" to "escalated", and ai_resolution is set to False
        (since the AI could not resolve it alone).

        After escalation:
        - The conversation appears in the agent dashboard's escalated queue.
        - notification_service sends alerts to available agents.
        - The AI stops auto-responding; human agents take over.

        Args:
            conversation_id: The conversation to escalate.

        Returns:
            The updated conversation dict from Supabase.
        """
        result = (
            self.db.table("conversations")
            .update({
                "status": "escalated",
                "ai_resolution": False,  # The AI could not resolve this one
            })
            .eq("id", conversation_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    async def resolve(self, conversation_id: str, agent_id: str | None = None) -> dict:
        """
        Mark a conversation as resolved (completed successfully).

        This can be called automatically when the AI resolves a conversation,
        or manually by a human agent after they've helped the customer. If an
        agent resolved it, their ID is recorded.

        Args:
            conversation_id: The conversation to resolve.
            agent_id: The ID of the agent who resolved it (None if AI-resolved).

        Returns:
            The updated conversation dict from Supabase.
        """
        update_data = {
            "status": "resolved",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
        if agent_id:
            update_data["assigned_agent_id"] = agent_id

        result = (
            self.db.table("conversations")
            .update(update_data)
            .eq("id", conversation_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    async def assign_agent(self, conversation_id: str, agent_id: str) -> dict:
        """
        Assign a specific human agent to handle a conversation.

        This is used by the agent dashboard when an agent claims or is assigned
        to an escalated conversation. It records which agent is responsible
        for this conversation.

        Args:
            conversation_id: The conversation to assign.
            agent_id: The ID of the agent taking ownership.

        Returns:
            The updated conversation dict from Supabase.
        """
        result = (
            self.db.table("conversations")
            .update({"assigned_agent_id": agent_id})
            .eq("id", conversation_id)
            .execute()
        )
        return result.data[0] if result.data else {}
