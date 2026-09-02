"""
Tests for the genre preset prompts.

These guard a bug that made the product look broken: selecting a different
preset appeared to change nothing, because three of the six genres are strictly
grounded ("answer ONLY from the context"). With an empty knowledge base there
was no context, so support/sales/booking all produced the same "I don't have
that information" reply — and because that scores as low confidence, the
handoff fired and the answer was replaced by the bot's single static
fallback_message. Three presets therefore returned a byte-identical reply until
a document was uploaded.

The assertions below are mostly about the prompts being *different from each
other*, which is the property that actually failed.
"""

from app.services.bot_genres import BOT_GENRES, build_system_prompt, get_genre

BASE_BOT = {"name": "Acme", "tone": "friendly"}
NO_DOCS = "No relevant documents found."
WITH_DOCS = "[Source 1] Returns are accepted within 30 days."


def prompt_for(genre: str, *, has_context: bool, **overrides) -> str:
    bot = {**BASE_BOT, "bot_type": genre, **overrides}
    context = WITH_DOCS if has_context else NO_DOCS
    return build_system_prompt(bot, context, "", has_context=has_context)


class TestPresetsAreDistinct:
    def test_all_six_differ_with_an_empty_knowledge_base(self):
        # The exact case that was broken.
        prompts = {g: prompt_for(g, has_context=False) for g in BOT_GENRES}
        assert len(set(prompts.values())) == len(BOT_GENRES)

    def test_all_six_differ_when_documents_exist(self):
        prompts = {g: prompt_for(g, has_context=True) for g in BOT_GENRES}
        assert len(set(prompts.values())) == len(BOT_GENRES)

    def test_every_genre_carries_its_own_instructions(self):
        for genre, config in BOT_GENRES.items():
            prompt = prompt_for(genre, has_context=True)
            first_bullet = config["extra_instructions"].split("\n")[0]
            assert first_bullet in prompt

    def test_roles_appear_in_the_identity_line(self):
        assert "customer support assistant" in prompt_for("support", has_context=True)
        assert "sales assistant" in prompt_for("sales", has_context=True)
        # The character genre has no role -- its identity is the persona.
        character = prompt_for("character", has_context=True, persona="a grumpy wizard")
        assert "a grumpy wizard" in character


class TestEmptyKnowledgeBase:
    def test_grounded_genres_drop_the_only_from_context_rule(self):
        # "Answer using ONLY the context" is meaningless with no context, and
        # is what collapsed every grounded preset into the same dead end.
        for genre in ("support", "sales", "booking"):
            assert "ONLY the context" not in prompt_for(genre, has_context=False)
            assert "ONLY the context" in prompt_for(genre, has_context=True)

    def test_grounded_genres_still_forbid_inventing_specifics(self):
        # Relaxing the grounding must not become a licence to hallucinate.
        for genre in ("support", "sales", "booking"):
            prompt = prompt_for(genre, has_context=False)
            assert "Do NOT invent specifics" in prompt

    def test_each_genre_has_its_own_empty_kb_behaviour(self):
        fallbacks = {
            g: BOT_GENRES[g]["no_kb_instructions"] for g in ("support", "sales", "booking")
        }
        assert len(set(fallbacks.values())) == 3
        for genre, instruction in fallbacks.items():
            assert instruction in prompt_for(genre, has_context=False)

    def test_character_genre_is_unaffected_by_missing_context(self):
        # Free conversation never depended on the knowledge base.
        assert prompt_for("character", has_context=False) == prompt_for(
            "character", has_context=True
        ).replace(WITH_DOCS, NO_DOCS)


class TestConfidenceAndHandoff:
    def test_handoff_genres_get_the_confidence_tag(self):
        for genre in ("support", "sales", "booking"):
            assert "[Confidence: X/10]" in prompt_for(genre, has_context=True)

    def test_non_handoff_genres_never_ask_for_confidence(self):
        for genre in ("tutor", "coding", "character"):
            assert "[Confidence:" not in prompt_for(genre, has_context=False)
            assert "[Confidence:" not in prompt_for(genre, has_context=True)

    def test_empty_kb_reframes_confidence_so_the_fallback_stops_firing(self):
        # Without this the model rates every answer low, trips the <0.5 handoff
        # threshold, and its reply is swapped for the static fallback_message.
        prompt = prompt_for("sales", has_context=False)
        assert "NOT whether documents were available" in prompt
        assert "NOT whether documents were available" not in prompt_for(
            "sales", has_context=True
        )


class TestOverrideAndFallbacks:
    def test_custom_prompt_override_replaces_the_preset(self):
        prompt = prompt_for("support", has_context=True, system_prompt_override="You are a duck.")
        assert prompt.startswith("You are a duck.")
        assert "customer support assistant" not in prompt

    def test_unknown_bot_type_falls_back_to_support(self):
        assert get_genre("nonsense") is BOT_GENRES["support"]
        assert get_genre(None) is BOT_GENRES["support"]

    def test_custom_rules_are_included(self):
        prompt = prompt_for("support", has_context=True, custom_rules=["Never discuss refunds"])
        assert "Never discuss refunds" in prompt
