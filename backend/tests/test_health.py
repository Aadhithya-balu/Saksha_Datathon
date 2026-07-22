"""Basic smoke test for the health check endpoint."""


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
