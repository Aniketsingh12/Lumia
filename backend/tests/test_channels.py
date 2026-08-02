from app.services.channel_router import ChannelRouter


class TestChannelRouter:
    def setup_method(self):
        self.router = ChannelRouter()

    def test_normalize_whatsapp(self):
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "919876543210",
                            "type": "text",
                            "text": {"body": "Hello"},
                        }],
                        "contacts": [{"profile": {"name": "Test User"}}],
                    }
                }]
            }]
        }
        msg = self.router.normalize_whatsapp(payload)
        assert msg is not None
        assert msg.channel == "whatsapp"
        assert msg.sender_id == "919876543210"
        assert msg.text == "Hello"
        assert msg.sender_name == "Test User"

    def test_normalize_whatsapp_no_messages(self):
        payload = {"entry": [{"changes": [{"value": {"messages": []}}]}]}
        msg = self.router.normalize_whatsapp(payload)
        assert msg is None

    def test_normalize_instagram(self):
        payload = {
            "entry": [{
                "messaging": [{
                    "sender": {"id": "ig_12345"},
                    "message": {"text": "Hi from Instagram"},
                }]
            }]
        }
        msg = self.router.normalize_instagram(payload)
        assert msg is not None
        assert msg.channel == "instagram"
        assert msg.sender_id == "ig_12345"
        assert msg.text == "Hi from Instagram"

    def test_normalize_slack(self):
        payload = {
            "event": {
                "type": "message",
                "user": "U12345",
                "text": "Hello from Slack",
            }
        }
        msg = self.router.normalize_slack(payload)
        assert msg is not None
        assert msg.channel == "slack"
        assert msg.text == "Hello from Slack"

    def test_normalize_slack_bot_message_ignored(self):
        payload = {
            "event": {
                "type": "message",
                "bot_id": "B12345",
                "text": "Bot message",
            }
        }
        msg = self.router.normalize_slack(payload)
        assert msg is None
