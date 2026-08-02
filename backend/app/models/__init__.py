"""
Models Package - Central hub for all Pydantic data models in BotForge.

=== What are Pydantic models? ===
Pydantic is a Python library for data validation. Instead of manually checking
whether incoming JSON has the right fields and types, we define "models" (Python
classes) that describe the expected shape of the data. Pydantic automatically:
  - Validates that required fields are present
  - Converts values to the correct type when possible (e.g., string "5" -> int 5)
  - Returns clear error messages when data is invalid

=== Why this __init__.py file exists ===
This file makes the "models" folder behave as a Python package. By importing all
models here, the rest of the codebase can do:
    from app.models import UserCreate, BotResponse
instead of the longer:
    from app.models.user import UserCreate
    from app.models.bot import BotResponse

This is a convenience pattern that keeps import statements short and readable
throughout the project.

=== What each group of models represents ===
- User models:         Registration, login, and user/org profile responses
- Bot models:          Creating, updating, and viewing chatbot configurations
- Knowledge models:    Uploading documents and viewing processed text chunks
- Conversation models: Starting and viewing chat conversations
- Message models:      Individual messages within a conversation
- Analytics models:    Querying and viewing bot performance statistics
"""

# --- User-related models ---
# UserCreate:   Fields needed when a new user signs up (email, password, name, org)
# UserResponse: Fields returned to the frontend after login or profile fetch
# OrgResponse:  Fields describing the user's organization (plan, owner, etc.)
from app.models.user import UserCreate, UserResponse, OrgResponse

# --- Bot-related models ---
# BotCreate:   Fields needed to create a new chatbot (name, tone, messages)
# BotUpdate:   Fields that can be changed on an existing bot (all optional)
# BotResponse: Full bot details returned to the frontend
from app.models.bot import BotCreate, BotUpdate, BotResponse

# --- Knowledge / Document models ---
# DocUpload:     Metadata sent when uploading a document for the bot's knowledge base
# DocResponse:   Full document record returned after upload (includes processing status)
# ChunkResponse: A single text chunk extracted from a document after processing
from app.models.knowledge import DocUpload, DocResponse, ChunkResponse

# --- Conversation models ---
# ConversationCreate:   Fields needed to start a new conversation (bot_id, channel)
# ConversationResponse: Full conversation record with status, tags, message count, etc.
from app.models.conversation import ConversationCreate, ConversationResponse

# --- Message models ---
# MessageCreate:   Fields sent when a customer (or agent) sends a new message
# MessageResponse: Full message record including AI metadata (confidence, intent, sources)
from app.models.message import MessageCreate, MessageResponse

# --- Analytics models ---
# AnalyticsQuery:    Filters for requesting analytics (bot_id, date range)
# AnalyticsResponse: The complete analytics payload (stats, top questions, charts, etc.)
from app.models.analytics import AnalyticsQuery, AnalyticsResponse

# __all__ controls what gets exported when another module does:
#     from app.models import *
# Only the names listed here will be imported in that case. This prevents
# accidentally exposing internal helpers or intermediate classes.
__all__ = [
    "UserCreate", "UserResponse", "OrgResponse",
    "BotCreate", "BotUpdate", "BotResponse",
    "DocUpload", "DocResponse", "ChunkResponse",
    "ConversationCreate", "ConversationResponse",
    "MessageCreate", "MessageResponse",
    "AnalyticsQuery", "AnalyticsResponse",
]
