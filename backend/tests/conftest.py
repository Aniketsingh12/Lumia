import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_bot():
    return {
        "id": "test-bot-001",
        "org_id": "test-org-001",
        "name": "TestBot",
        "tone": "friendly",
        "greeting_message": "Hi! I'm TestBot.",
        "fallback_message": "I'm not sure, let me get help.",
        "custom_rules": ["Be concise"],
        "channels": {"website": True},
        "is_active": True,
    }


@pytest.fixture
def test_conversation():
    return {
        "id": "test-conv-001",
        "bot_id": "test-bot-001",
        "channel": "website",
        "customer_id": "customer-001",
        "status": "active",
    }


@pytest.fixture
def test_message():
    return {
        "bot_id": "test-bot-001",
        "message": "What is your return policy?",
        "channel": "website",
    }
