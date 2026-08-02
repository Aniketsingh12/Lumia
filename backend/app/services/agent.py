"""
Agent Service
==============

A tool-using agent built on top of `LLMClient.run_agent` and the tool
registry in `tools.py`. This is the *agentic* counterpart to the linear
`AIEngine.process_message` pipeline:

- `AIEngine` runs a fixed chain (intent → RAG → answer → confidence → handoff).
- `Agent` lets the LLM choose what to do — search the KB, escalate, collect a
  lead, look up the time — and chain those calls until it has an answer.

Why both:
    The linear pipeline is fast and predictable for short FAQ-style answers
    (one RAG pass, one LLM call). The agent shines on multi-step requests
    ("can someone call me about pricing tomorrow morning?") where the model
    needs to combine KB lookup, contact capture, and escalation in one turn.

How it fits in:
    - `routers/chat.py` exposes `POST /api/chat/agent` which calls
      `Agent.respond(...)`.
    - The trace of tool calls is returned to the client and persisted on the
      message so it shows up in the agent dashboard for debugging.
"""

from app.services.llm_client import LLMClient
from app.services.tools import build_tool_set
from app.services.bot_genres import get_genre


class Agent:
    """
    Orchestrates a single agent turn for a customer message.

    The class itself is small — most of the work lives in `LLMClient.run_agent`
    (the provider-specific tool-use loops) and in `tools.py` (the tools
    themselves). What this class owns:

    - Building the system prompt with bot personality + rules + history.
    - Picking the tool set for this bot.
    - Interpreting the resulting trace to set top-level flags
      (`handoff`, `lead_collected`).
    """

    def __init__(self):
        self.llm = LLMClient()

    async def respond(
        self,
        bot_id: str,
        message: str,
        conversation_history: list[dict],
        bot_config: dict,
    ) -> dict:
        """
        Run the agent for one customer message and return the result.

        Returns a dict with:
            answer (str):           Final text the customer should see.
            tool_calls (list):      Ordered trace of tool invocations.
            iterations (int):       How many model→tool round-trips happened.
            handoff (bool):         True if the agent invoked escalate_to_human.
            lead_collected (bool):  True if the agent invoked collect_contact.
        """
        bot_name = bot_config.get("name", "Assistant")
        tone = bot_config.get("tone", "friendly")
        rules = bot_config.get("custom_rules", [])
        rules_text = "\n".join(f"- {r}" for r in rules) if rules else "None"

        # Genre-aware identity: characters ARE their persona, other genres get
        # their registry role (support agent, sales assistant, tutor, ...).
        genre = get_genre(bot_config.get("bot_type"))
        persona = (bot_config.get("persona") or "").strip()
        if genre["role"] is None:
            identity = persona or "a friendly conversational companion"
            identity_line = f"You are {bot_name} — {identity}. Speak with a {tone} tone."
        else:
            identity_line = f"You are {bot_name}, a {tone} {genre['role']}."
            if persona:
                identity_line += f"\nCharacter details: {persona}"

        # Trim to last 10 turns so we don't blow context on long chats.
        history_text = ""
        if conversation_history:
            for m in conversation_history[-10:]:
                history_text += f"{m.get('role', 'customer')}: {m.get('content', '')}\n"

        # The system prompt is what makes the agent behave well — be specific
        # about WHEN to call each tool. The tool descriptions cover WHAT.
        system_prompt = f"""{identity_line}

Rules:
{rules_text}

Conversation so far:
{history_text}

You have tools available. Use them like this:
1. Always call `search_knowledge_base` first if the customer asks anything
   factual. Quote what you find ("According to our docs, ...").
2. If the customer wants to be contacted later, or shares contact details,
   call `collect_contact`.
3. If the knowledge base has nothing useful, the customer asks for a human,
   or it's a sensitive complaint, call `escalate_to_human` and then tell the
   customer a teammate will follow up shortly.
4. Use `get_current_datetime` for any time-aware reasoning.

Once you have what you need, write a single concise reply to the customer.
Stay in character as {bot_name} with a {tone} tone."""

        tools = build_tool_set(bot_id)
        result = await self.llm.run_agent(
            system_prompt=system_prompt,
            user_message=message,
            tools=tools,
        )

        # Derive top-level flags from the trace so the caller doesn't have to
        # re-parse it.
        names = [tc["name"] for tc in result["tool_calls"]]
        return {
            "answer": result["answer"],
            "tool_calls": result["tool_calls"],
            "iterations": result["iterations"],
            "handoff": "escalate_to_human" in names,
            "lead_collected": "collect_contact" in names,
        }
