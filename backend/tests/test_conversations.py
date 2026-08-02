import pytest


class TestConversationEndpoints:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Lumio API"
        assert data["version"] == "1.0.0"

    def test_unauthorized_access(self, client):
        response = client.get("/api/bots/")
        assert response.status_code == 403 or response.status_code == 401
