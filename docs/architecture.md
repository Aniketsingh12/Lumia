# BotForge Architecture

## System Overview

```
Users/Customers → Channel Webhooks → FastAPI → AI Engine → Response
                                         ↓
                                   Supabase (data)
                                   ChromaDB (vectors)
                                   Redis (cache/queue)
```

## Data Flow

### Document Upload
1. Owner uploads PDF via dashboard
2. File saved to Supabase Storage
3. Celery task queued in Redis
4. Worker: PyPDF2 extracts text → TextSplitter chunks → sentence-transformers embeds → ChromaDB stores

### Chat Message
1. Customer sends message (any channel)
2. Channel webhook → FastAPI → ChannelRouter normalizes
3. ConversationManager gets/creates conversation
4. AIEngine pipeline:
   - classify_intent() → FAQ/Order/Complaint/etc
   - rag_pipeline.query() → embed question → ChromaDB search → top 5 chunks
   - generate_answer() → Claude/Ollama with context + history
   - score_confidence() → 0-1 score
   - should_handoff() → if low confidence or complaint
5. Response formatted for channel and sent back
6. Analytics event logged

### Human Handoff
1. AI confidence < 0.5 → triggers handoff
2. Bot sends fallback message to customer
3. Conversation status → "escalated"
4. Notification sent to agents (dashboard + Slack)
5. Agent replies via dashboard → sent to customer on same channel

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Tailwind CSS, Zustand, Recharts |
| Backend | FastAPI, Python 3.11 |
| AI/LLM | Claude API / Ollama (local), sentence-transformers |
| RAG | LangChain TextSplitter, ChromaDB |
| Database | Supabase (PostgreSQL) |
| Queue | Celery + Redis |
| Real-time | WebSocket (FastAPI native) |
| Channels | Meta API (WhatsApp/IG), Slack Bolt, IMAP/SMTP |
