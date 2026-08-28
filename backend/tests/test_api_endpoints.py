import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from api_fastapi import app, DB_FILE, SAVES_DIR

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

def test_run_simulation_status(monkeypatch):
    monkeypatch.setattr("api_fastapi.footy_main.main", lambda: None)
    response = client.post("/run-simulation")
    assert response.status_code == 200
    json_data = response.json()
    assert "status" in json_data
    assert json_data["status"] in ["success", "busy"]

def test_saves_endpoints(tmp_path):
    # Guard: ensure DB file exists so create_save copies a real file
    if not Path(DB_FILE).exists():
        from database.session import init_db
        init_db()

    # Test listing saves (should be empty in isolated dir)
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

    # Path traversal must be rejected. Starlette routing rejects encoded slash
    # traversal with 404 (path won't match /load/{save_id}); the handler also
    # rejects unsafe single-segment ids with 400. Either way it's blocked.
    bad = client.post("/load/..%2F..%2F..%2Fetc")
    assert bad.status_code in (400, 404)

    # Unsafe single-segment save id (contains spaces) must be rejected by handler
    bad2 = client.post("/load/bad%20save_id")
    assert bad2.status_code in (400, 404)

