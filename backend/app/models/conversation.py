"""
Conversation Models - Pydantic schemas for chat conversation management.

=== What are Pydantic models? ===
Pydantic models are Python classes that validate and structure data. They
ensure the API receives correctly-formatted requests and returns consistent
responses, all with automatic type checking and helpful error messages.

=== What this file defines ===
This file contains schemas for managing conversations -- the container that
groups a series of messages between a customer and a bot (or human agent):
  - ConversationCreate:   Fields needed to start a new conversation
  - ConversationResponse: Full conversation data returned to the frontend
  - ConversationFilter:   Filter criteria for searching/listing conversations
  - AgentReply:           A human agent's reply to a conversation

=== What is a "conversation"? ===
A conversation represents one complete interaction session between a customer
and a bot. Think of it like a support ticket:
  - It starts when a customer sends their first message
  - It contains all back-and-forth messages (customer, AI, and agent)
  - It ends when the issue is resolved or escalated
  - It tracks metadata like satisfaction score and resolution status

=== Relationship to the database ===
The "conversations" table in the database stores one row per conversation.
Each conversation has many messages (stored in the "messages" table).
This is the central entity that ties together customers, bots, and messages.
"""

from pydantic import BaseModel
from datetime import datetime


class ConversationCreate(BaseModel):
    """
    Schema for starting a new conversation.

    Used by: POST /conversations endpoint (or created automatically on first message)
    Sent by: The chat widget when a visitor starts chatting, or the API on first message

    A new conversation is created when a customer first reaches out. The
    frontend sends the bot ID and channel, and optionally any known customer
    information.
    """

    # The bot that will handle this conversation. This determines which AI
    # configuration (tone, rules, knowledge base) is used for generating responses.
    bot_id: str

    # Which messaging platform this conversation is happening on.
    # The channel affects how messages are formatted and delivered:
    #   - "website":   The embeddable chat widget on the customer's site
    #   - "whatsapp":  WhatsApp Business API messages
    #   - "instagram": Instagram Direct Messages
    #   - "slack":     Slack workspace messages
    #   - "email":     Email-based support threads
    channel: str = "website"  # website | whatsapp | instagram | slack | email

    # A unique identifier for the customer, if known. For website visitors, this
    # might be a cookie-based ID or an anonymous UUID. For authenticated channels
    # like WhatsApp, it's the phone number or platform user ID.
    # None for completely anonymous visitors.
    customer_id: str | None = None

    # The customer's display name, if known. Might come from their messaging
    # profile or from a pre-chat form. Shown in the agent dashboard so support
    # staff can address customers by name.
    customer_name: str | None = None

    # Contact information for the customer (email, phone number, etc.).
    # Useful for follow-up if the conversation is escalated or resolved offline.
    # None when the customer hasn't provided contact details.
    customer_contact: str | None = None


class ConversationResponse(BaseModel):
    """
    Schema for conversation data returned by the API.

    Used by: All endpoints that return conversation data (list, get, etc.)
    Sent to: The "Conversations" tab in the dashboard, showing all active/past chats

    This is a comprehensive model containing everything needed to display a
    conversation in the agent dashboard: status, customer info, message preview,
    and metadata like satisfaction scores.
    """

    # Unique identifier for this conversation (UUID string from the database).
    id: str

    # The bot handling this conversation. Used to filter conversations by bot
    # and to load the correct bot configuration.
    bot_id: str

    # Which messaging channel this conversation is on. Shown as an icon/badge
    # in the conversation list (e.g., a WhatsApp icon for WhatsApp conversations).
    channel: str

    # The customer's unique identifier. Used to link multiple conversations
    # from the same customer and show conversation history.
    customer_id: str | None = None

    # The customer's display name. Shown as the conversation title in the
    # agent dashboard (e.g., "Jane Smith" or "Anonymous Visitor").
    customer_name: str | None = None

    # The customer's contact details for follow-up purposes.
    customer_contact: str | None = None

    # The current state of this conversation:
    #   - "active":    Ongoing, customer may send more messages
    #   - "resolved":  Issue was solved (by AI or human), conversation is closed
    #   - "escalated": AI couldn't help, waiting for a human agent to respond
    # This drives the visual state in the dashboard (e.g., color coding).
    status: str = "active"  # active | resolved | escalated

    # The user ID of the human agent assigned to this conversation.
    # None means no human is assigned (AI is handling it autonomously).
    # Set when a conversation is escalated or manually picked up by an agent.
    assigned_agent_id: str | None = None

    # Whether the conversation was resolved entirely by AI without human help.
    # True = AI answered all questions successfully.
    # False = A human agent had to step in at some point.
    # Used for calculating the AI resolution rate in analytics.
    ai_resolution: bool = True

    # Customer satisfaction rating (e.g., 1-5 stars) if the customer provided
    # feedback after the conversation. None if no feedback was given.
    # Feeds into the satisfaction_score metric in analytics.
    satisfaction_score: int | None = None

    # Tags applied to this conversation for categorization and filtering.
    # Examples: ["billing", "urgent"], ["product-question"], ["bug-report"]
    # Tags can be applied automatically by the AI or manually by agents.
    tags: list[str] = []

    # A preview of the most recent message in this conversation.
    # Shown in the conversation list view so agents can quickly scan without
    # opening each conversation. Truncated to a reasonable length.
    last_message: str | None = None

    # Total number of messages exchanged in this conversation.
    # Displayed as a quick indicator of conversation length/complexity.
    message_count: int = 0

    # When the first message was sent (conversation start time).
    # Used for sorting conversations and calculating response times.
    started_at: datetime | None = None

    # When the conversation was marked as resolved. None if still active or
    # escalated. Used to calculate resolution time in analytics.
    resolved_at: datetime | None = None


class ConversationFilter(BaseModel):
    """
    Schema for filtering and searching conversations.

    Used by: GET /conversations endpoint (as query parameters)
    Sent by: The filter controls in the Conversations dashboard tab

    All fields are optional -- providing none returns all conversations.
    Providing multiple fields combines them with AND logic (e.g., bot_id="X"
    AND status="active" returns only active conversations for bot X).
    """

    # Filter by a specific bot. None = show conversations from all bots.
    bot_id: str | None = None

    # Filter by messaging channel. None = show all channels.
    channel: str | None = None

    # Filter by conversation status. None = show all statuses.
    # Useful for views like "show me only escalated conversations."
    status: str | None = None

    # Filter by assigned agent. None = show all (assigned and unassigned).
    # Useful for agents to see only their own assigned conversations.
    assigned_agent_id: str | None = None


class AgentReply(BaseModel):
    """
    Schema for a human agent's reply to a conversation.

    Used by: POST /conversations/{conversation_id}/reply endpoint
    Sent by: The agent dashboard when a support staff member types a reply

    When a conversation is escalated to a human, the agent uses this to send
    their response. The backend creates a message with role="agent" (as opposed
    to "customer" or "ai") so the frontend can style it differently.
    """

    # The text content of the agent's reply message.
    # This is sent directly to the customer via the appropriate channel.
    content: str
