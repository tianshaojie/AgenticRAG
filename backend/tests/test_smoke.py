import pytest


@pytest.mark.integration
def test_health_and_ready(client) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert "checks" in ready.json()
