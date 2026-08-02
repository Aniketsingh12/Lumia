import pytest
from unittest.mock import AsyncMock, patch


class TestAIEngine:
    @pytest.mark.asyncio
    @patch("app.services.ai_engine.LLMClient")
    @patch("app.services.ai_engine.RAGPipeline")
    async def test_process_message(self, mock_rag_cls, mock_llm_cls):
        from app.services.ai_engine import AIEngine

        mock_llm = AsyncMock()
        mock_llm.chat = AsyncMock(side_effect=[
            "FAQ",  # intent classification
            "Yes, we ship to Mumbai! [Confidence: 9/10]",  # answer
        ])
        mock_llm_cls.return_value = mock_llm

        mock_rag = AsyncMock()
        mock_rag.query = AsyncMock(return_value=[
            {"content": "We ship across India", "metadata": {}, "distance": 0.1}
        ])
        mock_rag_cls.return_value = mock_rag

        engine = AIEngine()
        engine.llm = mock_llm
        engine.rag = mock_rag

        result = await engine.process_message(
            bot_id="test-bot",
            message="Do you ship to Mumbai?",
            conversation_history=[],
            bot_config={"name": "TestBot", "tone": "friendly", "custom_rules": []},
        )

        assert result["intent"] == "FAQ"
        assert result["confidence"] == 0.9
        assert result["handoff"] is False
        assert "Mumbai" in result["answer"]

    @pytest.mark.asyncio
    @patch("app.services.ai_engine.LLMClient")
    async def test_classify_intent(self, mock_llm_cls):
        from app.services.ai_engine import AIEngine

        mock_llm = AsyncMock()
        mock_llm.chat = AsyncMock(return_value="Complaint")
        mock_llm_cls.return_value = mock_llm

        engine = AIEngine()
        engine.llm = mock_llm

        result = await engine.classify_intent("I want a refund!")
        assert result == "Complaint"

    def test_confidence_scoring(self):
        import asyncio
        from app.services.ai_engine import AIEngine

        engine = AIEngine()

        # Test extraction from answer text
        score = asyncio.get_event_loop().run_until_complete(
            engine.score_confidence("Answer here [Confidence: 8/10]", [{"content": "chunk"}])
        )
        assert score == 0.8

    def test_handoff_logic(self):
        import asyncio
        from app.services.ai_engine import AIEngine

        engine = AIEngine()

        # Low confidence → handoff
        result = asyncio.get_event_loop().run_until_complete(
            engine.should_handoff(0.3, "FAQ", [])
        )
        assert result is True

        # High confidence → no handoff
        result = asyncio.get_event_loop().run_until_complete(
            engine.should_handoff(0.9, "FAQ", [])
        )
        assert result is False
