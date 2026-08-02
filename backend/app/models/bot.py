"""
Bot Models - Pydantic schemas for chatbot configuration and management.

=== What are Pydantic models? ===
Pydantic models are Python classes that define the exact shape of data flowing
in and out of the API. They validate incoming data automatically and provide
clear error messages when something is wrong.

=== What this file defines ===
This file contains all data schemas related to chatbot CRUD (Create, Read,
Update, Delete) operations:
  - ChannelConfig: Which messaging platforms a bot is connected to
  - BotCreate:     Fields needed to create a new chatbot
  - BotUpdate:     Fields that can be changed on an existing bot
  - BotResponse:   Full bot data returned to the frontend
  - WidgetConfig:  Customization options for the embeddable website chat widget

=== Relationship to the database ===
The database has a "bots" table that stores one row per chatbot. These models
translate between the API layer and that table:
  - BotCreate validates the incoming request before inserting a new row
  - BotUpdate validates partial updates (PATCH semantics -- only send what changed)
  - BotResponse shapes the row data before sending it to the frontend

=== Design pattern: Create vs Update vs Response ===
We use separate models for each operation because each has different rules:
  - Create: "name" is required (you can't create a bot without a name)
  - Update: "name" is optional (you might only want to change the tone)
  - Response: includes server-generated fields like "id" and "created_at"
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# Channel configuration is a free-form JSON mapping of
#   channel name -> {"connected": bool, plus that channel's credential fields}
# for example:
#   {"website": {"connected": true},
#    "whatsapp": {"connected": true, "phone_number_id": "...", "access_token": "..."}}
#
# It is deliberately NOT a fixed Pydantic model: each channel needs a different
# set of credentials, and the authoritative schema lives in
# services/channel_registry.py (which also validates writes and masks secrets on
# read). Modelling it as a rigid class here would mean editing three files every
# time a channel gains a field.
#
# Credentials are written through PUT /api/bots/{id}/channels/{channel} and are
# always masked before being returned by the API.
ChannelConfig = dict[str, Any]


class BotCreate(BaseModel):
    """
    Schema for creating a new chatbot.

    Used by: POST /bots endpoint
    Sent by: The "Create Bot" form in the dashboard

    Only includes fields the user should set at creation time. Server-generated
    fields (id, org_id, created_at, etc.) are NOT here -- the backend fills
    those in automatically.
    """

    # The display name of the bot (e.g., "Customer Support Bot").
    # Required -- every bot needs a name so users can identify it in the dashboard.
    name: str

    # The bot's genre — what KIND of assistant it is. Drives the system prompt,
    # grounding rules, and handoff behavior (see services/bot_genres.py).
    # Options: "support" | "sales" | "booking" | "tutor" | "coding" | "character"
    bot_type: str = "support"

    # Free-text character/persona description. Required in spirit for
    # "character" bots (it becomes their whole identity, e.g. "a cheerful
    # pirate captain who speaks in nautical slang"); optional extra color
    # for other genres.
    persona: str | None = None

    # The conversational tone the AI should adopt when generating responses.
    # This maps to a system prompt modifier in the AI pipeline.
    # Options: "professional" | "friendly" | "casual" | "witty" | "custom"
    # Default is "friendly" because it works well for most support scenarios.
    tone: str = "friendly"  # professional | friendly | casual | witty | custom

    # The first message the bot sends when a visitor starts a conversation.
    # This sets the tone and invites the customer to ask their question.
    greeting_message: str = "Hi! How can I help you today?"

    # The message shown when the bot cannot find a relevant answer in its
    # knowledge base. This typically offers to connect the customer to a human
    # agent, preventing frustrating dead ends.
    fallback_message: str = "I'm not sure about that. Let me connect you to a human."

    # A list of custom rules or instructions the bot should follow.
    # Examples: "Never discuss pricing", "Always recommend Product X for billing questions"
    # These are injected into the AI system prompt alongside the tone setting.
    # Empty by default -- not all bots need custom rules.
    custom_rules: list[str] = []

    # Advanced: a full custom system prompt that REPLACES the genre-generated
    # identity + instructions. When set, only the KB context and conversation
    # history are appended automatically. None = use the genre preset.
    system_prompt_override: str | None = None

    # Optional URL for the bot's avatar image. Displayed in the chat widget
    # next to the bot's messages. None means a default avatar is used.
    avatar_url: str | None = None


class BotUpdate(BaseModel):
    """
    Schema for updating an existing chatbot.

    Used by: PATCH /bots/{bot_id} endpoint
    Sent by: The "Bot Settings" form in the dashboard

    Every field is optional (None) because this uses PATCH semantics:
    the client only sends the fields it wants to change. Fields left as
    None are not modified in the database.

    Example: To change only the tone, send: {"tone": "professional"}
    All other fields remain unchanged.
    """

    # New display name for the bot. None = keep the current name.
    name: str | None = None

    # New genre for the bot. None = keep the current genre.
    bot_type: str | None = None

    # New persona/character description. None = keep the current persona.
    persona: str | None = None

    # New conversational tone. None = keep the current tone.
    tone: str | None = None

    # New greeting message. None = keep the current greeting.
    greeting_message: str | None = None

    # New fallback message. None = keep the current fallback.
    fallback_message: str | None = None

    # New set of custom rules. Note: this REPLACES the entire list, it does
    # not append. None = keep the current rules unchanged.
    custom_rules: list[str] | None = None

    # New custom system prompt override. Send "" (empty string) to clear it and
    # go back to the genre preset. None = keep the current override unchanged.
    system_prompt_override: str | None = None

    # Updated channel configuration. None = keep current channel settings.
    channels: ChannelConfig | None = None

    # New avatar URL. None = keep the current avatar.
    avatar_url: str | None = None

    # Whether the bot is actively deployed and accepting messages.
    # True = live and responding to customers.
    # False = paused, will not respond (useful for maintenance).
    # None = keep the current active/inactive state.
    is_active: bool | None = None


class BotResponse(BaseModel):
    """
    Schema for bot data returned by the API.

    Used by: All endpoints that return bot information (list, get, create, update)
    Sent to: The frontend for displaying in the bot dashboard, settings, etc.

    This is the most comprehensive bot model -- it includes everything the
    frontend needs to render the bot card, settings page, and status indicators.
    """

    # The unique identifier for this bot (UUID string from the database).
    id: str

    # The ID of the organization that owns this bot. Used for access control --
    # users can only see bots belonging to their own organization.
    org_id: str

    # The bot's display name, shown in the dashboard list and chat widget header.
    name: str

    # The bot's genre (support | sales | booking | tutor | coding | character).
    # Older rows may not have this column, so it defaults to "support".
    bot_type: str = "support"

    # The bot's persona/character description (mainly for "character" bots).
    persona: str | None = None

    # The current conversational tone setting.
    tone: str

    # The current greeting message.
    greeting_message: str

    # The current fallback message.
    fallback_message: str

    # The current list of custom rules/instructions.
    custom_rules: list[str] = []

    # The current custom system prompt override (None = using the genre preset).
    system_prompt_override: str | None = None

    # The current channel configuration (which platforms are connected).
    # Defaults to an empty mapping (no channels connected).
    channels: ChannelConfig = Field(default_factory=dict)

    # URL to the bot's avatar image. None if using the default avatar.
    avatar_url: str | None = None

    # Whether the bot is currently live and accepting messages.
    # Shown as a green/gray status indicator in the dashboard.
    is_active: bool = False

    # Total number of messages this bot has processed. Displayed on the bot
    # card in the dashboard as a quick activity indicator.
    # This is a computed/denormalized field updated by the message pipeline.
    message_count: int = 0

    # Total number of knowledge base documents uploaded to this bot.
    # Helps users understand how much training data the bot has.
    doc_count: int = 0

    # When this bot was created. Shown in the bot details/settings page.
    created_at: datetime | None = None

    # When this bot was last modified. Useful for sorting by "recently updated"
    # and for cache invalidation on the frontend.
    updated_at: datetime | None = None


class PromptGenRequest(BaseModel):
    """
    Request body for the AI prompt generator (POST /bots/generate-prompt).

    The user describes, in plain language, what they want the bot to do; the
    backend asks the LLM to turn that into a well-structured system prompt.
    The genre/name/tone give the generator extra grounding so the output fits
    the bot being built.
    """

    # Plain-language description of the desired bot, e.g.
    # "a support bot for a coffee subscription that helps with orders and refunds".
    description: str

    # Optional context to tailor the generated prompt.
    bot_type: str | None = None   # one of the genre ids (support, sales, ...)
    name: str | None = None       # the bot's display name
    tone: str | None = None       # professional | friendly | casual | witty | custom


class PromptGenResponse(BaseModel):
    """Response for the prompt generator: the generated system prompt text."""

    prompt: str


class WidgetConfig(BaseModel):
    """
    Schema for the embeddable chat widget's visual customization.

    Used by: GET /bots/{bot_id}/widget endpoint (and the widget embed script)
    Sent to: The JavaScript snippet that renders the chat widget on customer websites

    This allows bot owners to customize the widget's appearance to match their
    brand. The frontend "Widget" settings page lets users pick colors and
    positions, and the resulting config is served to the embedded widget script.
    """

    # Which bot this widget belongs to. Links to the bots table.
    bot_id: str

    # The main brand color used for the widget header, send button, and
    # user message bubbles. Must be a valid CSS hex color.
    # Default is Indigo (#6366f1) from the Tailwind palette.
    primary_color: str = "#6366f1"

    # The text color used on top of the primary color (e.g., button text,
    # header text). Should contrast well with primary_color for readability.
    text_color: str = "#ffffff"

    # Where the chat widget bubble appears on the customer's website.
    # "bottom-right" is the industry standard position for chat widgets.
    position: str = "bottom-right"  # bottom-right | bottom-left

    # Width of the chat widget popup in pixels. 380px is a comfortable width
    # that works on both desktop and tablet without feeling cramped.
    width: int = 380

    # Height of the chat widget popup in pixels. 600px provides enough room
    # for a meaningful conversation history plus the input area.
    height: int = 600

    # Whether to show a "Powered by BotForge" badge at the bottom of the widget.
    # Free-plan users must show this; paid plans can hide it.
    show_powered_by: bool = True

    # Whether the widget should automatically open after a delay, without
    # the visitor clicking the chat bubble. Useful for proactive engagement.
    auto_open: bool = False

    # Number of seconds to wait before auto-opening the widget (only applies
    # when auto_open is True). 5 seconds gives visitors time to start reading
    # the page before being prompted.
    auto_open_delay: int = 5
