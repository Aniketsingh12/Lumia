import pytest


class TestConversationEndpoints:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root(self, client):
        """
        `/` has two valid contracts, so assert whichever applies here.

        In the production single-service image the React dashboard is bundled in
        and `/` serves it. With no dashboard built (CI, and local dev where the
        frontend runs separately under `npm run dev`) it reports API status
        instead. Hard-coding the JSON contract made this test fail purely
        because someone had run a frontend build in their checkout.
        """
        from app.main import _SERVE_FRONTEND

        response = client.get("/")
        assert response.status_code == 200

        if _SERVE_FRONTEND:
            assert response.headers["content-type"].startswith("text/html")
        else:
            data = response.json()
            assert data["name"] == "Lumio API"
            assert data["version"] == "1.0.0"

    def test_unauthorized_access(self, client):
        response = client.get("/api/bots/")
        assert response.status_code == 403 or response.status_code == 401
