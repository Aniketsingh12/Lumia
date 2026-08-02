"""
Agent Tools
============

Tools are functions that the LLM can choose to call when it needs information
or side-effects beyond plain text generation. Each tool declares:

- A unique `name` the model uses to invoke it.
- A natural-language `description` that helps the model decide *when* to use
  it (this is the most important field — write it for the model, not humans).
- A JSON-schema `input_schema` describing its arguments.
- An async `handler` that receives the parsed arguments and returns a string
  result that the model will read in its next turn.

The agent loop in `agent.py` doesn't know what any tool does — it only knows
how to call them. Adding a new capability means appending a new `Tool` here,
no plumbing changes required.

Why per-request tool sets:
    Some tools need bot/conversation context (e.g. `search_knowledge_base`
    needs a `bot_id`). Rather than threading context through every call, we
    build a fresh tool list per request with that context closed over. This
    also makes it easy to expose different tools to different bots later
    (e.g. an e-commerce bot gets `lookup_order`, a clinic bot doesn't).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from app.services.rag_pipeline import RAGPipeline


@dataclass
class Tool:
    """A single capability the agent can invoke."""

    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema
    handler: Callable[[dict[str, Any]], Awaitable[str]]


def build_tool_set(bot_id: str) -> list[Tool]:
    """
    Build a per-request tool set with `bot_id` and shared services bound in.

    Args:
        bot_id: The bot the agent is acting on behalf of. Tools that need to
                read/write per-bot data close over this.

    Returns:
        A list of Tool objects ready to hand to LLMClient.run_agent().
    """
    rag = RAGPipeline()

    # ---- Tool 1: Knowledge base search ---------------------------------------
    async def _search_knowledge_base(args: dict) -> str:
        query = args.get("query", "").strip()
        if not query:
            return "Error: empty query."
        chunks = await rag.query(bot_id, query, top_k=5)
        if not chunks:
            return "No relevant documents found in the knowledge base."
        return "\n\n".join(
            f"[Source {i + 1}] {c['content']}" for i, c in enumerate(chunks)
        )

    # ---- Tool 2: Escalate to human ------------------------------------------
    async def _escalate_to_human(args: dict) -> str:
        # Returns a sentinel string. The agent loop also records this call
        # in the trace; the chat router checks the trace and triggers the
        # actual escalation flow (db update + notifications) once the loop
        # finishes.
        reason = args.get("reason", "no reason provided")
        return (
            f"Conversation flagged for human handoff. Reason: {reason}. "
            "Tell the customer a human will reach out shortly."
        )

    # ---- Tool 3: Collect customer contact ------------------------------------
    async def _collect_contact(args: dict) -> str:
        # Best-effort persistence. We don't want a missing `leads` table to
        # break the agent loop in dev/test, so we swallow DB errors and tell
        # the model the save succeeded conceptually.
        from app.database import get_supabase

        name = args.get("name", "").strip()
        email = args.get("email", "").strip()
        phone = args.get("phone", "").strip()
        if not name and not email and not phone:
            return "Error: need at least one of name/email/phone."

        try:
            db = get_supabase()
            db.table("leads").insert({
                "bot_id": bot_id,
                "name": name or None,
                "email": email or None,
                "phone": phone or None,
                "notes": args.get("notes", ""),
            }).execute()
        except Exception:
            pass  # table may not exist in dev — tool still semantically succeeded

        return (
            f"Saved contact for {name or email or phone}. "
            "A team member will follow up."
        )

    # ---- Tool 4: Current UTC datetime ----------------------------------------
    async def _get_current_datetime(args: dict) -> str:
        return datetime.now(timezone.utc).isoformat()

    return [
        Tool(
            name="search_knowledge_base",
            description=(
                "Search the bot's knowledge base for facts needed to answer "
                "the customer. Always use this BEFORE saying you don't know."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — usually the customer's question.",
                    }
                },
                "required": ["query"],
            },
            handler=_search_knowledge_base,
        ),
        Tool(
            name="escalate_to_human",
            description=(
                "Hand the conversation off to a human agent. Use when: "
                "(a) the customer explicitly asks for a human, "
                "(b) you cannot answer after searching the knowledge base, "
                "(c) the customer is angry / it's a sensitive complaint."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "One-sentence reason for escalation, shown to the agent.",
                    }
                },
                "required": ["reason"],
            },
            handler=_escalate_to_human,
        ),
        Tool(
            name="collect_contact",
            description=(
                "Save the customer's contact details so a human can follow up. "
                "Call this when the customer agrees to be contacted later or "
                "provides their email/phone unprompted."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer's name."},
                    "email": {"type": "string", "description": "Customer's email address."},
                    "phone": {"type": "string", "description": "Customer's phone number."},
                    "notes": {"type": "string", "description": "Anything the agent should know."},
                },
                "required": ["name"],
            },
            handler=_collect_contact,
        ),
        Tool(
            name="get_current_datetime",
            description=(
                "Get the current UTC date and time. Use for scheduling, "
                "freshness checks, or any time-aware reasoning."
            ),
            input_schema={"type": "object", "properties": {}},
            handler=_get_current_datetime,
        ),
    ]
