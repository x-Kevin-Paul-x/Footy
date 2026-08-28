import pytest
from fastapi.testclient import TestClient
from api_fastapi import app
from logic.match_engine_grf import FORMATION_COORDINATES

client = TestClient(app)

def test_engine_status_endpoint():
    response = client.get("/api/v1/engine/status")
    assert response.status_code == 200
    data = response.json()
    assert "engine_mode" in data
    assert "grf_available" in data
    assert "checkpoint_found" in data
    assert "baller_dir" in data

def test_match_video_endpoint_missing():
    response = client.get("/api/v1/match/nonexistent_match/video")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == "nonexistent_match"
    assert data["available"] is False

def test_simulate_grf_match_endpoint():
    payload = {
        "home_team_name": "Arsenal",
        "away_team_name": "Chelsea",
        "home_formation": "4-3-3",
        "away_formation": "4-2-3-1",
        "generate_video": False,
        "max_steps": 500
    }
    response = client.post("/api/v1/match/simulate-grf", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["home_team"] == "Arsenal"
    assert data["away_team"] == "Chelsea"
    assert "home_score" in data
    assert "away_score" in data
    assert "possession" in data
    assert "shots" in data
    assert "xg" in data
    assert "timeline" in data

def test_formation_coordinates_bounds():
    for form_name, coords in FORMATION_COORDINATES.items():
        assert len(coords) == 11, f"Formation {form_name} must have 11 player coordinates"
        for x, y in coords:
            assert -1.0 <= x <= 1.0, f"Coordinate x={x} out of range in {form_name}"
            assert -0.45 <= y <= 0.45, f"Coordinate y={y} out of range in {form_name}"
