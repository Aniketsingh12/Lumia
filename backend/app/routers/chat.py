"""
Chat Router
============

This router handles real-time messaging between customers and AI bots. It provides
both a REST endpoint (for simple request/response chat) and a WebSocket endpoint
(for real-time bidirectional communication), plus a feedback endpoint.

Endpoints provided:
    POST /            - Send a message and get an AI response (REST)
    WS   /ws/{id}     - Real-time WebSocket chat for a specific conversation
    POST /feedback    - Submit feedback (thumbs up/down) on a specific AI message

How Chat Works (High-Level Flow):
    1. Customer sends a message (via REST POST or WebSocket).
    2. The message is saved to the conversation history in the database.
    3. Previous conversation history is loaded for context.
    4. The AI engine processes the message:
       a. Searches the bot's knowledge base (RAG) for relevant content
       b. Generates a response using the LLM with conversation history + retrieved context
       c. Returns the answer, confidence score, detected intent, and source references
    5. If confidence is too low (handoff=True), the bot escalates to a human agent
       instead of giving a potentially wrong answer.
    6. The AI response is saved and broadcast to any connected WebSocket clients.
    7. The response is returned to the caller.

WebSocket vs REST:
    - REST (POST /): Simple request-response. Client sends a message, waits for
      the AI reply, gets it back in the HTTP response. Best for widget embeds.
    - WebSocket (WS /ws/{id}): Persistent connection. Messages flow in both directions
      in real time. Best for live dashboard views where agents watch conversations.
      Multiple clients can connect to the same conversation and all receive broadcasts.

Connection Manager:
    The ConnectionManager class tracks active WebSocket connections grouped by
    conversation_id. When a new message arrives (from REST or WebSocket), the
    response is broadcast to ALL connected WebSocket clients for that conversation.
    This enables real-time updates in the agent dashboard.
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse

from app.models.message import ChatRequest, ChatResponse, ChatFeedback, MessageResponse
from app.services.ai_engine import AIEngine
from app.services.agent import Agent
from app.services.conversation_manager import ConversationManager
from app.services.notification_service import notify_escalation
from app.middleware.auth import get_current_user
from app.database import get_supabase

# Create the router instance. Mounted with prefix like "/api/chat".
router = APIRouter()

# Legacy reference kept for backward compatibility (some modules may import this).
connected_clients: dict[str, list[WebSocket]] = {}


class ConnectionManager:
    """
    Manages active WebSocket connections grouped by conversation ID.

    This allows multiple clients (e.g., multiple agent browser tabs) to subscribe
    to the same conversation and receive real-time message updates.

    Attributes:
        active: A dictionary mapping conversation_id -> list of WebSocket connections.
    """

    def __init__(self):
        # Maps conversation_id to a list of active WebSocket connections
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, conversation_id: str, ws: WebSocket):
        """
        Accept a new WebSocket connection and register it for a conversation.

        Args:
            conversation_id: The conversation this client wants to subscribe to.
            ws: The WebSocket connection to register.
        """
        await ws.accept()
        if conversation_id not in self.active:
            self.active[conversation_id] = []
        self.active[conversation_id].append(ws)

    def disconnect(self, conversation_id: str, ws: WebSocket):
        """
        Remove a WebSocket connection when a client disconnects.

        Args:
            conversation_id: The conversation the client was subscribed to.
            ws: The WebSocket connection to remove.
        """
        if conversation_id in self.active:
            self.active[conversation_id].remove(ws)

    async def broadcast(self, conversation_id: str, message: dict):
        """
        Send a message to ALL WebSocket clients subscribed to a conversation.

        This is how real-time updates work: when a new message is added to a
        conversation (from any source -- REST, WebSocket, or channel webhook),
        we broadcast it to all connected clients so they see it instantly.

        Args:
            conversation_id: The conversation to broadcast to.
            message: The message payload (dict) to send as JSON.
        """
        if conversation_id in self.active:
            for ws in self.active[conversation_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    # If sending fails (e.g., client disconnected ungracefully),
                    # silently skip. The client will be cleaned up on next disconnect.
                    pass


# Singleton instance used by this router and imported by other modules
# (e.g., conversations.py imports this to broadcast agent replies).
manager = ConnectionManager()


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send a customer message and receive an AI-generated response.

    HTTP Method: POST
    URL: /
    Auth Required: No (this is a public endpoint used by the chat widget)

    Request Body (ChatRequest):
        - bot_id (str): The UUID of the bot to chat with
        - message (str): The customer's message text
        - channel (str): The channel this message came from (e.g., "web", "whatsapp")
        - customer_id (str, optional): Unique identifier for the customer
        - customer_name (str, optional): Display name of the customer

    Request Flow:
        1. Initialize the AI engine and conversation manager.
        2. Get or create a conversation for this customer+bot+channel combination.
           If the customer has chatted with this bot on this channel before,
           their existing conversation is reused to maintain context.
        3. Save the customer's message to the conversation history.
        4. Load the full conversation history (for context in the AI prompt).
        5. Load the bot's configuration (tone, rules, greeting, fallback message).
        6. Send the message through the AI engine, which:
           a. Searches the knowledge base for relevant document chunks (RAG)
           b. Builds a prompt with: system instructions + bot config + history + context
           c. Calls the LLM (e.g., OpenAI GPT) to generate a response
           d. Returns: answer text, confidence score, detected intent, sources, handoff flag
        7. If handoff is True (AI confidence is too low):
           - Send the bot's fallback message instead of the AI answer
           - Mark the conversation as escalated
           - Send a notification to human agents
           - Return the response with handoff=True
        8. If handoff is False (AI is confident):
           - Save the AI response to the conversation
           - Broadcast the response to any connected WebSocket clients
           - Return the response with the AI answer and metadata

    Response (ChatResponse):
        - message (MessageResponse): The AI's response message with metadata
        - conversation_id (str): The conversation this message belongs to
        - sources (list, optional): Knowledge base chunks used to generate the answer
        - confidence (float): How confident the AI is in its answer (0.0 to 1.0)
        - intent (str): The detected intent of the customer's message
        - handoff (bool): Whether the conversation was escalated to a human
    """
    ai_engine = AIEngine()
    conv_manager = ConversationManager()

    # Get or create conversation -- reuses existing conversation for same customer+bot+channel
    conversation = await conv_manager.get_or_create(
        bot_id=request.bot_id,
        channel=request.channel,
        customer_id=request.customer_id,
        customer_name=request.customer_name,
    )
    conversation_id = conversation["id"]

    # Save customer message to the database
    await conv_manager.add_message(
        conversation_id=conversation_id,
        role="customer",
        content=request.message,
    )

    # Get conversation history for AI context (previous messages in this conversation)
    history = await conv_manager.get_history(conversation_id)

    # Get bot config (tone, rules, fallback message, etc.)
    db = get_supabase()
    bot_result = db.table("bots").select("*").eq("id", request.bot_id).execute()
    bot_config = bot_result.data[0] if bot_result.data else {}

    # Process through AI engine (RAG search + LLM generation)
    result = await ai_engine.process_message(
        bot_id=request.bot_id,
        message=request.message,
        conversation_history=history,
        bot_config=bot_config,
    )

    # Handle handoff: AI is not confident enough to answer, escalate to human agent
    if result["handoff"]:
        fallback = bot_config.get("fallback_message", "Let me connect you to a human.")
        await conv_manager.add_message(
            conversation_id=conversation_id,
            role="ai",
            content=fallback,
            meta={"confidence_score": result["confidence"], "intent": result["intent"]},
        )
        # Mark the conversation as escalated in the database
        await conv_manager.escalate(conversation_id)
        # Notify human agents (e.g., via email, Slack, or in-app notification)
        await notify_escalation(
            conversation_id,
            bot_config.get("name", "Bot"),
            request.customer_name,
        )

        return ChatResponse(
            message=MessageResponse(
                id="",
                conversation_id=conversation_id,
                role="ai",
                content=fallback,
                confidence_score=result["confidence"],
                intent=result["intent"],
            ),
            conversation_id=conversation_id,
            confidence=result["confidence"],
            intent=result["intent"],
            handoff=True,
        )

    # Save AI response to conversation history
    ai_message = await conv_manager.add_message(
        conversation_id=conversation_id,
        role="ai",
        content=result["answer"],
        meta={
            "source_chunks": result["sources"],
            "confidence_score": result["confidence"],
            "intent": result["intent"],
        },
    )

    # Broadcast via WebSocket so any connected dashboard clients see the new message
    await manager.broadcast(conversation_id, {
        "type": "new_message",
        "message": ai_message,
    })

    return ChatResponse(
        message=MessageResponse(
            id=ai_message.get("id", ""),
            conversation_id=conversation_id,
            role="ai",
            content=result["answer"],
            source_chunks=result["sources"],
            confidence_score=result["confidence"],
            intent=result["intent"],
        ),
        conversation_id=conversation_id,
        sources=result["sources"],
        confidence=result["confidence"],
        intent=result["intent"],
        handoff=False,
    )


@router.post("/agent")
async def send_message_agent(request: ChatRequest):
    """
    Send a message to a tool-using agent.

    Unlike `POST /` (linear RAG pipeline), this endpoint lets the LLM decide
    which tools to call and in what order. Available tools today:
    `search_knowledge_base`, `collect_contact`, `escalate_to_human`,
    `get_current_datetime` — defined in `app/services/tools.py`.

    The response includes the final answer **plus the full tool-call trace**,
    which is also persisted on the message so it appears in the agent
    dashboard for transparency / debugging.
    """
    agent = Agent()
    conv_manager = ConversationManager()

    conversation = await conv_manager.get_or_create(
        bot_id=request.bot_id,
        channel=request.channel,
        customer_id=request.customer_id,
        customer_name=request.customer_name,
    )
    conversation_id = conversation["id"]

    await conv_manager.add_message(
        conversation_id=conversation_id,
        role="customer",
        content=request.message,
    )

    history = await conv_manager.get_history(conversation_id)
    db = get_supabase()
    bot_result = db.table("bots").select("*").eq("id", request.bot_id).execute()
    bot_config = bot_result.data[0] if bot_result.data else {}

    result = await agent.respond(
        bot_id=request.bot_id,
        message=request.message,
        conversation_history=history,
        bot_config=bot_config,
    )

    # If the agent decided to escalate, run the same handoff flow as the
    # linear pipeline (mark conversation, notify agents).
    if result["handoff"]:
        await conv_manager.escalate(conversation_id)
        await notify_escalation(
            conversation_id,
            bot_config.get("name", "Bot"),
            request.customer_name,
        )

    ai_message = await conv_manager.add_message(
        conversation_id=conversation_id,
        role="ai",
        content=result["answer"],
        meta={
            "tool_calls": result["tool_calls"],
            "iterations": result["iterations"],
            "handoff": result["handoff"],
            "lead_collected": result["lead_collected"],
        },
    )
    await manager.broadcast(conversation_id, {
        "type": "new_message",
        "message": ai_message,
    })

    return {
        "conversation_id": conversation_id,
        "answer": result["answer"],
        "tool_calls": result["tool_calls"],
        "iterations": result["iterations"],
        "handoff": result["handoff"],
        "lead_collected": result["lead_collected"],
    }


@router.post("/stream")
async def send_message_stream(request: ChatRequest):
    """
    Stream an AI response token-by-token via Server-Sent Events.

    Same flow as POST `/` but returns `text/event-stream`. Each SSE event has a
    `data:` JSON payload of one of these shapes:

        {"type": "intent",  "intent": "FAQ"}
        {"type": "sources", "sources": [...], "chunks_used": 3}
        {"type": "token",   "delta": "Hello"}      # many of these
        {"type": "done",    "answer": "...", "confidence": 0.86,
         "intent": "FAQ", "handoff": false, "sources": [...]}
        {"type": "handoff", "answer": "<fallback>", "confidence": 0.2}

    The widget renders `token` deltas live and finalizes the message on `done`
    or `handoff`. Confidence and handoff can only be decided after the full
    answer is generated, so they ship with the final event.
    """
    ai_engine = AIEngine()
    conv_manager = ConversationManager()

    conversation = await conv_manager.get_or_create(
        bot_id=request.bot_id,
        channel=request.channel,
        customer_id=request.customer_id,
        customer_name=request.customer_name,
    )
    conversation_id = conversation["id"]

    await conv_manager.add_message(
        conversation_id=conversation_id,
        role="customer",
        content=request.message,
    )

    history = await conv_manager.get_history(conversation_id)
    db = get_supabase()
    bot_result = db.table("bots").select("*").eq("id", request.bot_id).execute()
    bot_config = bot_result.data[0] if bot_result.data else {}

    async def event_generator():
        # Tell the client which conversation this is so it can reconnect later
        yield f"data: {json.dumps({'type': 'conversation', 'conversation_id': conversation_id})}\n\n"

        final_event: dict | None = None
        async for event in ai_engine.stream_message(
            bot_id=request.bot_id,
            message=request.message,
            conversation_history=history,
            bot_config=bot_config,
        ):
            if event["type"] == "done":
                final_event = event
            yield f"data: {json.dumps(event)}\n\n"

        if final_event is None:
            return

        # Persist the final message + handle handoff after the stream completes
        if final_event.get("handoff"):
            fallback = bot_config.get("fallback_message", "Let me connect you to a human.")
            await conv_manager.add_message(
                conversation_id=conversation_id,
                role="ai",
                content=fallback,
                meta={
                    "confidence_score": final_event["confidence"],
                    "intent": final_event["intent"],
                },
            )
            await conv_manager.escalate(conversation_id)
            await notify_escalation(
                conversation_id,
                bot_config.get("name", "Bot"),
                request.customer_name,
            )
            yield f"data: {json.dumps({'type': 'handoff', 'answer': fallback, 'confidence': final_event['confidence']})}\n\n"
        else:
            ai_message = await conv_manager.add_message(
                conversation_id=conversation_id,
                role="ai",
                content=final_event["answer"],
                meta={
                    "source_chunks": final_event["sources"],
                    "confidence_score": final_event["confidence"],
                    "intent": final_event["intent"],
                },
            )
            await manager.broadcast(conversation_id, {
                "type": "new_message",
                "message": ai_message,
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering (nginx)
            "Connection": "keep-alive",
        },
    )


@router.websocket("/ws/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    """
    Real-time WebSocket endpoint for bidirectional chat.

    URL: /ws/{conversation_id}
    Protocol: WebSocket (ws:// or wss://)
    Auth Required: No (WebSocket auth is typically handled via query params or initial message)

    Path Parameters:
        - conversation_id (str): The UUID of the conversation to connect to

    How WebSocket Chat Works:
        1. Client opens a WebSocket connection to /ws/{conversation_id}.
        2. The server accepts the connection and registers it with the ConnectionManager.
        3. The server enters an infinite loop, waiting for incoming messages.
        4. When the client sends a message (JSON text), it is processed:
           a. The message type is checked (currently only "message" type is handled)
           b. The customer message is saved to the conversation
           c. Conversation history is loaded
           d. The AI engine generates a response
           e. The AI response is saved
           f. The response is broadcast to ALL connected WebSocket clients
              (including the sender), so everyone sees the update in real time
        5. When the client disconnects (WebSocketDisconnect exception), the
           connection is removed from the ConnectionManager.

    Expected Incoming Message Format (JSON):
        {
            "type": "message",
            "content": "Hello, I need help with...",
            "bot_id": "uuid-of-the-bot"
        }

    Broadcast Message Format (sent to all connected clients):
        {
            "type": "new_message",
            "message": { ... message data from database ... }
        }

    Why WebSocket in Addition to REST:
        - WebSocket provides instant, push-based updates without polling.
        - Multiple agents can watch the same conversation in real time.
        - The chat widget can receive AI responses as soon as they are ready.
    """
    await manager.connect(conversation_id, websocket)
    try:
        while True:
            # Wait for an incoming message from the client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Process incoming WebSocket message (same logic as the REST endpoint)
            if message.get("type") == "message":
                ai_engine = AIEngine()
                conv_manager = ConversationManager()

                # Save the customer's message
                await conv_manager.add_message(
                    conversation_id=conversation_id,
                    role="customer",
                    content=message["content"],
                )

                # Load conversation history for AI context
                history = await conv_manager.get_history(conversation_id)

                # Load bot configuration
                db = get_supabase()
                bot_id = message.get("bot_id", "")
                bot_result = db.table("bots").select("*").eq("id", bot_id).execute()
                bot_config = bot_result.data[0] if bot_result.data else {}

                # Generate AI response
                result = await ai_engine.process_message(
                    bot_id=bot_id,
                    message=message["content"],
                    conversation_history=history,
                    bot_config=bot_config,
                )

                # Save AI response to the database
                ai_msg = await conv_manager.add_message(
                    conversation_id=conversation_id,
                    role="ai",
                    content=result["answer"],
                    meta={
                        "source_chunks": result["sources"],
                        "confidence_score": result["confidence"],
                        "intent": result["intent"],
                    },
                )

                # Broadcast the AI response to ALL connected clients for this conversation
                await manager.broadcast(conversation_id, {
                    "type": "new_message",
                    "message": ai_msg,
                })

    except WebSocketDisconnect:
        # Client disconnected -- clean up the connection from the manager
        manager.disconnect(conversation_id, websocket)


@router.post("/feedback")
async def submit_feedback(feedback: ChatFeedback):
    """
    Submit feedback on a specific AI message (e.g., thumbs up/down).

    HTTP Method: POST
    URL: /feedback
    Auth Required: No (customers can submit feedback from the chat widget)

    Request Body (ChatFeedback):
        - message_id (str): The UUID of the AI message being rated
        - rating (str): The feedback rating (e.g., "positive", "negative")
        - comment (str, optional): Additional feedback text from the customer

    Request Flow:
        1. Update the message record in the "messages" table with the feedback
           rating and optional comment.
        2. Return a confirmation.

    This feedback data is used by the analytics system to track customer satisfaction
    and identify areas where the bot's responses could be improved.

    Response: {"message": "Feedback recorded"}
    """
    db = get_supabase()
    db.table("messages").update({
        "feedback": feedback.rating,
        "feedback_comment": feedback.comment,
    }).eq("id", feedback.message_id).execute()

    return {"message": "Feedback recorded"}
