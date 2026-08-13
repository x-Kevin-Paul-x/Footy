from fastapi.testclient import TestClient
from api_fastapi import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Footy API"}

def test_get_teams_endpoint():
    response = client.get("/teams")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_players_endpoint():
    response = client.get("/players")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_seasons_endpoint():
    response = client.get("/get-seasons")
    assert response.status_code == 200
    assert "seasons" in response.json()
    assert isinstance(response.json()["seasons"], list)

def test_run_simulation_status():
    response = client.post("/run-simulation")
    assert response.status_code == 200
    json_data = response.json()
    assert "status" in json_data
    assert json_data["status"] in ["success", "busy"]

def test_saves_endpoints():
    # Test listing saves
    response = client.get("/saves")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Test creating save
    create_resp = client.post("/saves")
    assert create_resp.status_code == 200
    data = create_resp.json()
    assert data["status"] == "success"
    save_id = data["save_id"]

    # Test loading save
    load_resp = client.post(f"/load/{save_id}")
    assert load_resp.status_code == 200
    assert load_resp.json()["status"] == "success"
