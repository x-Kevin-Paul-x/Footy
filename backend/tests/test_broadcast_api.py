from fastapi.testclient import TestClient

from api_fastapi import app
from logic.grf_native_runner import GRFNativeRunner


client = TestClient(app)


def _result():
    return {
        "score": [1, 0], "events": [], "possession": [50.0, 50.0],
        "shots": [1, 0], "xg": [0.1, 0.0], "video_url": None,
    }


def _install_runner_spy(monkeypatch):
    captured = []

    def fake_simulate(self, **kwargs):
        captured.append(kwargs)
        return _result()

    monkeypatch.setattr(GRFNativeRunner, "simulate", fake_simulate)
    monkeypatch.setattr("database.match_db.get_match_details", lambda _match_id: None)
    monkeypatch.setattr("database.db_setup.get_current_simulation_run", lambda: None)
    return captured


def test_simulate_grf_propagates_explicit_state_recording_request(monkeypatch):
    captured = _install_runner_spy(monkeypatch)
    response = client.post("/api/v1/match/simulate-grf", json={
        "match_id": "broadcast_state_propagation", "home_team_name": "Arsenal",
        "away_team_name": "Chelsea", "max_steps": 100,
        "record_grf_states": True, "record_dump": False,
    })
    assert response.status_code == 200
    assert captured[-1]["record_grf_states"] is True


def test_simulate_grf_keeps_legacy_no_state_default(monkeypatch):
    captured = _install_runner_spy(monkeypatch)
    response = client.post("/api/v1/match/simulate-grf", json={
        "match_id": "broadcast_state_default", "home_team_name": "Arsenal",
        "away_team_name": "Chelsea", "max_steps": 100, "record_dump": False,
    })
    assert response.status_code == 200
    assert captured[-1]["record_grf_states"] is False
