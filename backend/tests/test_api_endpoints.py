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


def test_find_match_video_and_url_direct_and_run_dir(tmp_path, monkeypatch):
    from api_fastapi import find_match_video_and_url
    test_recordings = tmp_path / "recordings"
    test_recordings.mkdir(parents=True)
    monkeypatch.setattr("api_fastapi.RECORDINGS_DIR", test_recordings)

    # 1. Root match video
    v_root = test_recordings / "match_99991.mp4"
    v_root.write_bytes(b"dummy_video_content")
    p, url = find_match_video_and_url("99991")
    assert p == v_root
    assert url == "/recordings/match_99991.mp4"

    # 2. Run directory match video
    run_dir = test_recordings / "run_test_abc"
    run_dir.mkdir(parents=True)
    v_run = run_dir / "match_99992.mp4"
    v_run.write_bytes(b"dummy_video_content_2")
    p2, url2 = find_match_video_and_url("99992")
    assert p2 == v_run
    assert url2 == "/recordings/run_test_abc/match_99992.mp4"

    # 3. Missing video
    p3, url3 = find_match_video_and_url("nonexistent_match")
    assert p3 is None
    assert url3 is None


def test_simulate_grf_preserves_existing_video(monkeypatch, tmp_path):
    test_recordings = tmp_path / "recordings"
    test_recordings.mkdir(parents=True)
    monkeypatch.setattr("api_fastapi.RECORDINGS_DIR", test_recordings)

    # Place video for match 8888
    v_file = test_recordings / "match_8888.mp4"
    v_file.write_bytes(b"fake_mp4_bytes")

    # Mock get_match_details to return a match with score 3 - 1
    mock_details = {
        "match_id": 8888,
        "home_team_name": "Arsenal",
        "away_team_name": "Chelsea",
        "home_goals": 3,
        "away_goals": 1,
        "home_possession": 62.5,
        "away_possession": 37.5,
        "home_shots": [1, 2, 3, 4],
        "away_shots": [1],
        "events": [{"minute": 15, "type": "GOAL", "player": "Saka"}],
        "video_url": "/recordings/match_8888.mp4",
    }
    monkeypatch.setattr("database.match_db.get_match_details", lambda mid: mock_details if str(mid) == "8888" else None)

    resp = client.post("/api/v1/match/simulate-grf", json={
        "match_id": "8888",
        "home_team_name": "Arsenal",
        "away_team_name": "Chelsea",
        "generate_video": True
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["home_score"] == 3
    assert data["away_score"] == 1
    assert data["video_url"] == "/recordings/match_8888.mp4"
    assert len(data["timeline"]) == 1


def test_get_matches_for_season_optimized():
    from database.match_db import get_matches_for_season
    matches = get_matches_for_season(2025)
    assert isinstance(matches, list)


def test_match_collection_route_is_distinct_from_match_detail(monkeypatch):
    expected = [{"match_id": 2026, "season_year": 2026}]
    monkeypatch.setattr("database.match_db.get_matches_for_season", lambda year: expected if year == 2026 else [])

    collection = client.get("/api/v1/seasons/2026/matches")

    assert collection.status_code == 200
    assert collection.json() == {"matches": expected}


def test_get_all_players_with_joinedload():
    from database.player_db import get_all_players
    players = get_all_players()
    assert isinstance(players, list)


def test_get_match_details_string_and_composite_ids(tmp_path):
    from database.session import get_db_session
    from database.models import Match, MatchShots, MatchEvent
    from database.match_db import get_match_details

    with get_db_session() as db:
        m = Match(
            match_number=42,
            season_year=2026,
            home_team_id=1,
            away_team_id=2,
            date="2026-08-15",
            home_goals=2,
            away_goals=1,
            home_possession=55.0,
            away_possession=45.0,
            weather="Sunny",
            intensity="Normal"
        )
        db.add(m)
        db.flush()
        db.add(MatchShots(match_id=m.match_id, team="home", total=10, on_target=5))
        db.add(MatchShots(match_id=m.match_id, team="away", total=6, on_target=2))
        db.add(MatchEvent(match_id=m.match_id, minute=30, type="goal", player="Star Striker", team="home", details="Goal!"))
        db.commit()
        assigned_id = m.match_id

    # Test lookup by integer ID
    res_int = get_match_details(assigned_id)
    assert res_int is not None
    assert res_int["match_id"] == assigned_id
    assert res_int["home_goals"] == 2
    assert len(res_int["events"]) == 1

    # Test lookup by string integer ID
    res_str = get_match_details(str(assigned_id))
    assert res_str is not None
    assert res_str["match_id"] == assigned_id

    # Test lookup by "match_{id}" format
    res_prefix = get_match_details(f"match_{assigned_id}")
    assert res_prefix is not None
    assert res_prefix["match_id"] == assigned_id

    # Test lookup by composite season fixture "match_2026_1_2"
    res_comp = get_match_details("match_2026_1_2")
    assert res_comp is not None
    assert res_comp["match_id"] == assigned_id
    assert res_comp["shots"]["home"]["total"] == 10
