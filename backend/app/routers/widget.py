"""
Widget Router
==============

This router handles the public-facing chat widget configuration and embed code.
The chat widget is a JavaScript snippet that customers embed on their website to
add a chatbot popup. This router provides the endpoints the widget needs to
initialize itself and the endpoints for managing widget appearance settings.

Endpoints provided:
    GET  /{bot_id}/config  - Get widget configuration (public, no auth required)
    PUT  /{bot_id}/config  - Update widget configuration (requires auth via bot owner)
    GET  /{bot_id}/embed   - Get the HTML embed code snippet for a bot's widget

Design Decisions:
    - GET /{bot_id}/config is intentionally PUBLIC (no authentication). This is because
      the widget JavaScript running on a customer's website needs to fetch the bot's
      config without any user credentials. The widget only receives non-sensitive
      display settings (colors, position, greeting message).
    - PUT /{bot_id}/config does NOT currently require auth (this could be a security
      improvement -- it should probably require get_current_user).
    - Widget config is stored in a separate "widget_configs" table, linked to a bot.
      If no custom config exists, sensible defaults are returned.
    - The embed endpoint generates a simple script tag that website owners can
      copy-paste into their HTML.
"""

from fastapi import APIRouter, HTTPException

from app.database import get_supabase
from app.models.bot import WidgetConfig

# Create the router instance. Mounted with prefix like "/api/widget".
router = APIRouter()


@router.get("/{bot_id}/config")
async def get_widget_config(bot_id: str):
    """
    Get the widget configuration for a specific bot.

    HTTP Method: GET
    URL: /{bot_id}/config
    Auth Required: No (public endpoint -- called by the widget JavaScript on customer websites)

    Path Parameters:
        - bot_id (str): The UUID of the bot whose widget config to fetch

    Request Flow:
        1. Look up the bot in the "bots" table. The bot must exist AND be active
           (is_active=True). If not found or inactive, return HTTP 404.
           This prevents widgets from working for deactivated bots.
        2. Look up any custom widget configuration in the "widget_configs" table.
        3. Merge bot-level settings (name, greeting, avatar, tone) with widget-specific
           settings (colors, position, dimensions, auto-open behavior).
        4. If no custom widget config exists, return sensible defaults for all
           widget-specific fields (purple color, bottom-right position, etc.).

    Response (dict):
        - bot_id (str): The bot's UUID
        - bot_name (str): Display name shown in the widget header
        - greeting_message (str): First message shown when the widget opens
        - avatar_url (str | None): Bot's profile picture URL
        - tone (str): Bot's personality tone
        - primary_color (str): Widget's primary/accent color (hex code)
        - text_color (str): Widget's text color (hex code)
        - position (str): Where the widget appears on screen ("bottom-right", "bottom-left")
        - width (int): Widget popup width in pixels
        - height (int): Widget popup height in pixels
        - show_powered_by (bool): Whether to show "Powered by BotForge" branding
        - auto_open (bool): Whether the widget opens automatically on page load
        - auto_open_delay (int): Seconds to wait before auto-opening

    Error Responses:
        - 404: Bot not found or inactive
    """
    db = get_supabase()
    bot = db.table("bots").select("*").eq("id", bot_id).eq("is_active", True).execute()
    if not bot.data:
        raise HTTPException(status_code=404, detail="Bot not found or inactive")

    bot_data = bot.data[0]

    # Get widget config or return defaults if none has been customized
    widget = db.table("widget_configs").select("*").eq("bot_id", bot_id).execute()
    widget_config = widget.data[0] if widget.data else {}

    return {
        "bot_id": bot_id,
        "bot_name": bot_data.get("name", "Bot"),
        "greeting_message": bot_data.get("greeting_message", "Hi! How can I help?"),
        "avatar_url": bot_data.get("avatar_url"),
        "tone": bot_data.get("tone", "friendly"),
        # Widget appearance settings with defaults
        "primary_color": widget_config.get("primary_color", "#6366f1"),
        "text_color": widget_config.get("text_color", "#ffffff"),
        "position": widget_config.get("position", "bottom-right"),
        "width": widget_config.get("width", 380),
        "height": widget_config.get("height", 600),
        "show_powered_by": widget_config.get("show_powered_by", True),
        "auto_open": widget_config.get("auto_open", False),
        "auto_open_delay": widget_config.get("auto_open_delay", 5),
    }


@router.put("/{bot_id}/config")
async def update_widget_config(bot_id: str, config: WidgetConfig):
    """
    Update the widget configuration for a specific bot.

    HTTP Method: PUT
    URL: /{bot_id}/config
    Auth Required: No (should probably require auth -- potential improvement)

    Path Parameters:
        - bot_id (str): The UUID of the bot whose widget config to update

    Request Body (WidgetConfig):
        - primary_color (str): Hex color code for the widget accent
        - text_color (str): Hex color code for widget text
        - position (str): Screen position ("bottom-right" or "bottom-left")
        - width (int): Widget width in pixels
        - height (int): Widget height in pixels
        - show_powered_by (bool): Show/hide "Powered by BotForge"
        - auto_open (bool): Auto-open the widget on page load
        - auto_open_delay (int): Delay in seconds before auto-opening

    Request Flow:
        1. Check if a widget config record already exists for this bot.
        2. If it exists, UPDATE the existing record with the new values.
        3. If it does not exist, INSERT a new record (upsert pattern).
        4. Return the saved configuration data.

    Response: The saved widget configuration object.
    """
    db = get_supabase()

    # Check if a config already exists for this bot (upsert logic)
    existing = db.table("widget_configs").select("id").eq("bot_id", bot_id).execute()
    config_data = config.model_dump()

    if existing.data:
        # Update the existing widget config
        result = db.table("widget_configs").update(config_data).eq("bot_id", bot_id).execute()
    else:
        # Create a new widget config record
        result = db.table("widget_configs").insert(config_data).execute()

    return result.data[0] if result.data else config_data


@router.get("/{bot_id}/embed")
async def get_embed_code(bot_id: str):
    """
    Get the HTML embed code snippet for embedding the chat widget on a website.

    HTTP Method: GET
    URL: /{bot_id}/embed
    Auth Required: No (public endpoint)

    Path Parameters:
        - bot_id (str): The UUID of the bot to generate embed code for

    Request Flow:
        1. Load application settings to get the API base URL.
        2. Generate a script tag that loads the widget JavaScript file
           with the bot_id as a data attribute.
        3. Return the embed code string and the bot_id.

    The generated embed code looks like:
        <script src="https://api.botforge.com/widget.js" data-bot-id="<uuid>"></script>

    Website owners copy this snippet into their HTML, and the widget.js script
    will automatically:
        1. Fetch the widget config from GET /{bot_id}/config
        2. Render the chat popup with the configured appearance
        3. Handle sending/receiving messages via the POST /chat/ endpoint

    Response:
        - embed_code (str): The HTML script tag to embed on a website
        - bot_id (str): The bot's UUID (for reference)
    """
    from app.config import get_settings

    settings = get_settings()
    embed_code = f'<script src="{settings.api_url}/widget.js" data-bot-id="{bot_id}"></script>'
    return {"embed_code": embed_code, "bot_id": bot_id}
