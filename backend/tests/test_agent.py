"""
Tests for the tool-using Agent.

We don't hit any LLM provider — we patch `LLMClient.run_agent` to return a
canned trace and assert the Agent class extracts the right top-level flags.
We also exercise individual tool handlers directly.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.tools import build_tool_set


class TestAgent:
    @pytest.mark.asyncio
    @patch("app.services.agent.LLMClient")
    async def test_handoff_flag_set_when_escalate_tool_called(self, mock_llm_cls):
        from app.services.agent import Agent

        mock_llm = AsyncMock()
        mock_llm.run_agent = AsyncMock(return_value={
            "answer": "A teammate will reach out shortly.",
            "tool_calls": [
                {"name": "search_knowledge_base", "input": {"query": "refund"}, "result": "no docs"},
                {"name": "escalate_to_human", "input": {"reason": "needs human"}, "result": "ok"},
            ],
            "iterations": 2,
        })
        mock_llm_cls.return_value = mock_llm

        agent = Agent()
        result = await agent.respond(
            bot_id="test-bot",
            message="I want a refund",
            conversation_history=[],
            bot_config={"name": "TestBot", "tone": "friendly", "custom_rules": []},
        )

        assert result["handoff"] is True
        assert result["lead_collected"] is False
        assert result["iterations"] == 2
        assert "teammate" in result["answer"]

    @pytest.mark.asyncio
    @patch("app.services.agent.LLMClient")
    async def test_lead_collected_flag(self, mock_llm_cls):
        from app.services.agent import Agent

        mock_llm = AsyncMock()
        mock_llm.run_agent = AsyncMock(return_value={
            "answer": "Got it — we'll be in touch!",
            "tool_calls": [
                {"name": "collect_contact", "input": {"name": "Jane", "email": "j@x.com"}, "result": "saved"},
            ],
            "iterations": 1,
        })
        mock_llm_cls.return_value = mock_llm

        agent = Agent()
        result = await agent.respond(
            bot_id="test-bot",
            message="Email me at j@x.com",
            conversation_history=[],
            bot_config={"name": "TestBot", "tone": "friendly", "custom_rules": []},
        )

        assert result["lead_collected"] is True
        assert result["handoff"] is False


class TestToolHandlers:
    @pytest.mark.asyncio
    async def test_get_current_datetime_returns_iso(self):
        tools = build_tool_set("test-bot")
        now_tool = next(t for t in tools if t.name == "get_current_datetime")
        result = await now_tool.handler({})
        # ISO 8601 UTC timestamps end in +00:00
        assert "+00:00" in result or result.endswith("Z")

    @pytest.mark.asyncio
    async def test_escalate_returns_handoff_message(self):
        tools = build_tool_set("test-bot")
        esc = next(t for t in tools if t.name == "escalate_to_human")
        result = await esc.handler({"reason": "angry customer"})
        assert "human" in result.lower()
        assert "angry customer" in result

    @pytest.mark.asyncio
    async def test_collect_contact_requires_at_least_one_field(self):
        tools = build_tool_set("test-bot")
        collect = next(t for t in tools if t.name == "collect_contact")
        # All empty → error
        result = await collect.handler({"name": "", "email": "", "phone": ""})
        assert result.lower().startswith("error")
