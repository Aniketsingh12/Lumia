"""
Services Package for BotForge Backend
======================================

This package contains all the core business logic services that power BotForge.
Each service is a self-contained module responsible for one area of functionality.

Architecture Overview:
---------------------
When a customer message arrives (from WhatsApp, Instagram, Slack, or the website),
it flows through these services in roughly this order:

1. **channel_router.py** - Normalizes the incoming message from any channel into
   a common format (UnifiedMessage). This means the rest of the system does not
   need to know which platform the message came from.

2. **conversation_manager.py** - Looks up (or creates) the conversation in the
   database (Supabase). Stores every message exchanged between the customer and
   the bot so we have a full history.

3. **voice_processor.py** - If the message contains audio (e.g., a WhatsApp voice
   note), this service downloads and transcribes it to text using OpenAI Whisper.

4. **image_processor.py** - If the message contains an image, this service
   downloads and describes it using Claude Vision so the AI can "see" what the
   customer sent.

5. **ai_engine.py** - The brain of the system. Takes the text message, classifies
   the customer's intent, searches the knowledge base via RAG, generates an answer,
   scores its own confidence, and decides whether to hand off to a human agent.

6. **llm_client.py** - A thin wrapper around multiple LLM providers (Claude,
   OpenAI, Ollama). The AI engine and other services call this instead of talking
   to LLM APIs directly, making it easy to swap providers.

7. **rag_pipeline.py** - Manages the knowledge base. Ingests documents by splitting
   them into chunks, embedding them, and storing them in ChromaDB. At query time,
   it finds the most relevant chunks for a given question.

8. **notification_service.py** - Sends alerts (e.g., to Slack) when a conversation
   is escalated to a human agent.

9. **analytics_service.py** - Crunches conversation and message data to produce
   dashboards: total messages, AI resolution rate, top questions, etc.

All services are designed to be used asynchronously (async/await) so they can
handle many concurrent requests without blocking.
"""
