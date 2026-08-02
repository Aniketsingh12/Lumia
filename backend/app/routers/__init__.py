"""
BotForge Backend Routers Package
=================================

This package contains all the API route handlers (routers) for the BotForge application.
Each router module defines a group of related API endpoints using FastAPI's APIRouter.

The routers are organized as follows:
    - auth.py           : User signup, login, and authentication (JWT-based)
    - bots.py           : CRUD operations for chatbot management
    - knowledge.py      : Document upload, URL ingestion, and knowledge base management
    - chat.py           : Real-time chat via REST and WebSocket, plus feedback
    - conversations.py  : Conversation listing, agent assignment, escalation, and replies
    - analytics.py      : Dashboard analytics, top questions, satisfaction scores, exports
    - widget.py         : Public-facing widget configuration and embed code generation
    - settings.py       : Organization settings, team management, webhooks, and API keys
    - channels/          : External messaging platform integrations (WhatsApp, Instagram, Slack, Email)

All routers are mounted onto the main FastAPI application in the app's main entry point,
typically with a URL prefix like "/api/auth", "/api/bots", etc.
"""
