"""
Bot Genres Registry
====================

Defines the different *kinds* of bots BotForge can build. Historically every
bot was hardcoded as a "customer support assistant"; this registry makes the
role a per-bot choice (`bot_type` on the bots table).

Each genre controls three things:

1. **role** — the identity line injected into the system prompt
   ("You are {name}, a {tone} <role>").

2. **grounded** — whether answers must come ONLY from the knowledge base.
   Grounded genres (support, sales, booking) cite sources and admit when the
   docs don't cover something. Ungrounded genres (character) chat freely.
   Soft-grounded genres (tutor, coding) prefer KB context when it exists but
   may fall back to general knowledge.

3. **allow_handoff** — whether low confidence escalates to a human agent.
   Support-style bots hand off; a chit-chat character never should.

The special "character" genre uses the bot's `persona` field as its entire
identity — e.g. "a cheerful pirate captain who speaks in nautical slang" —
enabling casual-chat companion bots.

Frontend note: `frontend/src/lib/genres.ts` mirrors the ids/labels below for
the genre picker UI (icons and copy live there). Keep the ids in sync.
"""

BOT_GENRES: dict[str, dict] = {
    "support": {
        "label": "Customer Support",
        "role": "customer support assistant",
        "grounding": "strict",   # answer only from KB, cite sources
        "allow_handoff": True,
        "extra_instructions": (
            "- Help customers resolve issues quickly and politely\n"
            "- If the context doesn't contain the answer, say so honestly"
        ),
    },
    "sales": {
        "label": "Sales Assistant",
        "role": "sales assistant",
        "grounding": "strict",
        "allow_handoff": True,
        "extra_instructions": (
            "- Highlight product benefits relevant to what the customer asks\n"
            "- Gently guide interested customers toward the next step (demo, trial, purchase)\n"
            "- Never invent prices, discounts, or features not present in the context"
        ),
    },
    "booking": {
        "label": "Booking Concierge",
        "role": "booking and reservations concierge",
        "grounding": "strict",
        "allow_handoff": True,
        "extra_instructions": (
            "- Help customers check availability, book, reschedule, or cancel\n"
            "- Collect the details a booking needs (date, time, party size, contact)\n"
            "- Confirm the details back to the customer before finalizing"
        ),
    },
    "tutor": {
        "label": "Tutor",
        "role": "patient tutor and educator",
        "grounding": "soft",     # prefer KB, but may teach from general knowledge
        "allow_handoff": False,
        "extra_instructions": (
            "- Explain concepts step by step, checking understanding as you go\n"
            "- Prefer the provided course material when it covers the topic\n"
            "- Use examples and analogies; encourage questions"
        ),
    },
    "coding": {
        "label": "Coding Assistant",
        "role": "programming assistant",
        "grounding": "soft",
        "allow_handoff": False,
        "extra_instructions": (
            "- Give working code examples in fenced code blocks\n"
            "- Prefer the project's own docs (the provided context) over general advice\n"
            "- Point out pitfalls and edge cases briefly"
        ),
    },
    "character": {
        "label": "Character / Companion",
        "role": None,            # identity comes entirely from the bot's persona
        "grounding": "none",     # free conversation, KB is optional flavor
        "allow_handoff": False,
        "extra_instructions": (
            "- Keep replies conversational and engaging, matching the character's voice\n"
            "- Never break character or mention being an AI language model\n"
            "- Keep responses reasonably short, like a real chat"
        ),
    },
}

DEFAULT_GENRE = "support"


def get_genre(bot_type: str | None) -> dict:
    """Return the genre config for a bot_type, falling back to support."""
    return BOT_GENRES.get(bot_type or DEFAULT_GENRE, BOT_GENRES[DEFAULT_GENRE])


def build_system_prompt(bot_config: dict, context_text: str, history_text: str) -> str:
    """
    Build the full chat system prompt for a bot based on its genre.

    Centralizes what used to be duplicated (and hardcoded to "customer support
    assistant") in ai_engine.generate_answer and ai_engine.stream_message.

    Args:
        bot_config: The bot row (name, tone, bot_type, persona, custom_rules...).
        context_text: Formatted RAG chunks ("[Source 1] ..." lines) or a
                      "no documents" placeholder.
        history_text: Formatted recent conversation history.

    Returns:
        The system prompt string for LLMClient.chat / chat_stream.
    """
    bot_name = bot_config.get("name", "Assistant")
    tone = bot_config.get("tone", "friendly")
    rules = bot_config.get("custom_rules", [])
    genre = get_genre(bot_config.get("bot_type"))
    persona = (bot_config.get("persona") or "").strip()

    # Only handoff-capable genres need the self-reported confidence tag (it
    # drives the escalation decision and is stripped from the final answer).
    confidence_line = (
        "- Rate your confidence from 1-10 at the end of your response like this: [Confidence: X/10]\n"
        if genre["allow_handoff"]
        else ""
    )

    # ── Custom override ──────────────────────────────────────────────────────
    # If the bot owner wrote their own system prompt, use it verbatim as the
    # identity + instructions. We still append the KB context and conversation
    # history (so RAG and memory keep working) plus the confidence tag when the
    # genre can hand off. This gives full control without breaking retrieval.
    override = (bot_config.get("system_prompt_override") or "").strip()
    if override:
        return f"""{override}

Context from knowledge base:
{context_text}

Conversation history:
{history_text}
{confidence_line}""".rstrip()

    # Identity line: characters ARE their persona; other genres get their role,
    # with persona (if set) as extra color.
    if genre["role"] is None:
        identity = persona or "a friendly conversational companion"
        identity_line = f"You are {bot_name} — {identity}. Speak with a {tone} tone."
    else:
        identity_line = f"You are {bot_name}, a {tone} {genre['role']}."
        if persona:
            identity_line += f"\nCharacter details: {persona}"

    rules_text = "\n".join(f"- {rule}" for rule in rules) if rules else "None"

    # Grounding rules differ per genre. Strict genres must not stray from the
    # KB; soft genres prefer it; "none" genres treat it as optional flavor.
    if genre["grounding"] == "strict":
        grounding_block = (
            "- Answer using ONLY the context provided above\n"
            "- Cite your sources (e.g., \"Based on Source 1...\")\n"
            "- If the context doesn't contain the answer, say so honestly"
        )
    elif genre["grounding"] == "soft":
        grounding_block = (
            "- Prefer the context provided above when it covers the question, and cite it\n"
            "- If the context doesn't cover it, you may answer from general knowledge"
        )
    else:
        grounding_block = (
            "- The context above is optional background — use it only if it's relevant\n"
            "- Chat naturally; you don't need to cite sources"
        )

    return f"""{identity_line}

Rules:
{rules_text}

Context from knowledge base:
{context_text}

Conversation history:
{history_text}

Instructions:
{grounding_block}
{genre["extra_instructions"]}
{confidence_line}- Stay in character as {bot_name} with a {tone} tone"""
