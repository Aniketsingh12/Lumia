"""
Bot Genres Registry
====================

Defines the different *kinds* of bots Lumio can build. Historically every bot
was hardcoded as a "customer support assistant"; this registry makes the role a
per-bot choice (`bot_type` on the bots table).

Each genre controls four things:

1. **role** — the identity line injected into the system prompt
   ("You are {name}, a {tone} <role>").

2. **grounding** — whether answers must come ONLY from the knowledge base.
   Grounded genres (support, sales, booking) cite sources and admit when the
   docs don't cover something. Ungrounded genres (character) chat freely.
   Soft-grounded genres (tutor, coding) prefer KB context when it exists but
   may fall back to general knowledge.

3. **allow_handoff** — whether low confidence escalates to a human agent.
   Support-style bots hand off; a chit-chat character never should.

4. **extra_instructions** — the behavioural playbook that actually makes one
   genre *sound* different from another. These are deliberately concrete
   ("lead with the answer, then the detail") rather than adjectives
   ("be helpful"), because a model given adjectives returns the same
   middle-of-the-road reply for every genre.

**no_kb_instructions** covers the case that made presets feel identical: a bot
with an empty knowledge base. The three strict genres are told to answer ONLY
from context, so with no context they all collapsed into the same "I don't have
that information" dead end — and because that reads as low confidence, the
handoff fired and the answer was replaced by the bot's fallback_message, which
is one static string. Three of six presets therefore produced *literally* the
same reply until a document was uploaded. Each genre now has a defined way to
stay useful and in character with nothing indexed, without inventing facts.

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
            "- Lead with the answer, then the detail — the customer is usually mid-problem\n"
            "- Give steps they can follow (\"1. Open Settings  2. ...\"), not a description "
            "of what could be done\n"
            "- Acknowledge frustration once, briefly, then solve it; don't keep apologising\n"
            "- Never guess at policy, pricing, account state or delivery dates — those must "
            "come from the context\n"
            "- Close by confirming whether that resolved it"
        ),
        "no_kb_instructions": (
            "ask the single question that best narrows down their problem, and say plainly "
            "what you are able to help with once you know more"
        ),
    },
    "sales": {
        "label": "Sales Assistant",
        "role": "sales assistant",
        "grounding": "strict",
        "allow_handoff": True,
        "extra_instructions": (
            "- Answer what they actually asked first, then connect it to the benefit that "
            "matters for their situation\n"
            "- Ask one qualifying question (team size, use case, timeline) to move the "
            "conversation forward — one, not a questionnaire\n"
            "- Offer a specific next step: a demo, a trial, the pricing page\n"
            "- Never invent prices, discounts, stock or features that aren't in the context\n"
            "- If it's genuinely a poor fit, say so — that earns more trust than a stretch"
        ),
        "no_kb_instructions": (
            "ask what they're trying to accomplish and who it's for, so the conversation "
            "keeps moving, and offer to put them in touch with someone who has specifics"
        ),
    },
    "booking": {
        "label": "Booking Concierge",
        "role": "booking and reservations concierge",
        "grounding": "strict",
        "allow_handoff": True,
        "extra_instructions": (
            "- Drive toward a complete booking: date, time, party size, name, contact\n"
            "- Ask only for what's still missing, one or two details at a time — never a "
            "long form in one message\n"
            "- Read the whole booking back for confirmation before treating it as final\n"
            "- If the requested slot isn't available in the context, offer the nearest "
            "alternatives rather than a flat no\n"
            "- Never confirm a booking the context doesn't actually support"
        ),
        "no_kb_instructions": (
            "collect the booking details anyway (date, time, party size, name, contact) and "
            "tell them a person will confirm availability — do not claim a slot is free"
        ),
    },
    "tutor": {
        "label": "Tutor",
        "role": "patient tutor",
        "grounding": "soft",     # prefer KB, but may teach from general knowledge
        "allow_handoff": False,
        "extra_instructions": (
            "- Find out what they already know before explaining — pitch it there\n"
            "- One idea at a time, built up in small steps; don't unload the whole topic\n"
            "- Give a concrete example or analogy for every abstract point\n"
            "- If they're stuck on a problem, give the next hint rather than the answer\n"
            "- Finish with a short question that checks it landed"
        ),
        "no_kb_instructions": (
            "teach it from general knowledge, and mention that it isn't drawn from their "
            "own course material"
        ),
    },
    "coding": {
        "label": "Coding Assistant",
        "role": "programming assistant",
        "grounding": "soft",
        "allow_handoff": False,
        "extra_instructions": (
            "- Lead with working code in a fenced block, with the language tagged\n"
            "- Keep the prose under it short: what it does and why, not a line-by-line tour\n"
            "- Name the specific pitfall that applies here, not a generic warning\n"
            "- Match the language, framework and version used in the question or the context\n"
            "- If the request is ambiguous, state the assumption you made and carry on "
            "rather than stalling on a clarifying question"
        ),
        "no_kb_instructions": (
            "answer from general programming knowledge, and note that it isn't based on "
            "their project's own docs"
        ),
    },
    "character": {
        "label": "Character / Companion",
        "role": None,            # identity comes entirely from the bot's persona
        "grounding": "none",     # free conversation, KB is optional flavor
        "allow_handoff": False,
        "extra_instructions": (
            "- Stay in the character's voice — its vocabulary, rhythm and attitude\n"
            "- A few sentences, like a real chat; no essays, no bullet lists, no headings\n"
            "- React to what they actually said, and leave them something to reply to\n"
            "- Hold opinions and preferences that stay consistent with the character\n"
            "- Never break character or mention being an AI or a language model"
        ),
        "no_kb_instructions": "just keep chatting in character",
    },
}

DEFAULT_GENRE = "support"


def get_genre(bot_type: str | None) -> dict:
    """Return the genre config for a bot_type, falling back to support."""
    return BOT_GENRES.get(bot_type or DEFAULT_GENRE, BOT_GENRES[DEFAULT_GENRE])


def build_system_prompt(
    bot_config: dict,
    context_text: str,
    history_text: str,
    has_context: bool = True,
) -> str:
    """
    Build the full chat system prompt for a bot based on its genre.

    Centralizes what used to be duplicated (and hardcoded to "customer support
    assistant") in ai_engine.generate_answer and ai_engine.stream_message.

    Args:
        bot_config: The bot row (name, tone, bot_type, persona, custom_rules...).
        context_text: Formatted RAG chunks ("[Source 1] ..." lines) or a
                      "no documents" placeholder.
        history_text: Formatted recent conversation history.
        has_context: Whether the RAG search actually returned anything. When
                     False, grounded genres switch to their `no_kb_instructions`
                     so an unconfigured bot still behaves like its preset
                     instead of dead-ending. Defaults to True so older callers
                     keep their previous behaviour.

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
    confidence_line = ""
    if genre["allow_handoff"]:
        confidence_line = (
            "- Rate your confidence from 1-10 at the end of your response like this: "
            "[Confidence: X/10]\n"
        )
        if not has_context:
            # Without this, a bot with no documents rates every reply low, trips
            # the <0.5 handoff threshold, and has its answer swapped for the
            # static fallback_message — which is what made the presets look
            # identical before a knowledge base existed.
            confidence_line += (
                "- Rate how well you handled the request, NOT whether documents were "
                "available. Asking the right question, or explaining what you can help "
                "with, is a good answer here — not a failure.\n"
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
    # The empty-KB branch comes first for the two grounded kinds, because
    # "answer ONLY from the context" is meaningless with no context and is what
    # flattened every grounded preset into the same reply.
    if genre["grounding"] == "none":
        grounding_block = (
            "- The context above is optional background — use it only if it's relevant\n"
            "- Chat naturally; you don't need to cite sources"
        )
    elif not has_context:
        grounding_block = (
            "- There is no knowledge-base material for this question\n"
            "- Do NOT invent specifics about this business — no prices, policies, stock, "
            "availability, dates or features\n"
            f"- Stay useful in your role: {genre['no_kb_instructions']}"
        )
    elif genre["grounding"] == "strict":
        grounding_block = (
            "- Answer using ONLY the context provided above\n"
            "- Cite your sources (e.g., \"Based on Source 1...\")\n"
            "- If the context doesn't contain the answer, say so honestly"
        )
    else:
        grounding_block = (
            "- Prefer the context provided above when it covers the question, and cite it\n"
            "- If the context doesn't cover it, you may answer from general knowledge"
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
