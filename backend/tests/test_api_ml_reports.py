import json
from fastapi.testclient import TestClient
import api_fastapi


def test_get_ml_reports_lists_available_reports(tmp_path, monkeypatch):
    report_path = tmp_path / "comparison_sample.json"
    report_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-03-11T03:00:00",
                "summary": {
                    "primary_policy": "dqn_best",
                    "best_policy_by_reward": "dqn_best",
                    "best_policy_by_points": "random",
                    "best_policy_by_position": "do_nothing",
                },
                "policies": {"dqn_best": {}, "random": {}},
                "config": {"episodes": 4},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(api_fastapi, "ML_REPORTS_DIR", tmp_path)

    client = TestClient(api_fastapi.app)
    response = client.get("/ml-reports")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["reports"]) == 1
    assert payload["reports"][0]["file_name"] == "comparison_sample.json"
    assert payload["reports"][0]["report_type"] == "comparison"
    assert payload["reports"][0]["policy_count"] == 2


def test_get_ml_report_returns_full_payload(tmp_path, monkeypatch):
    report_path = tmp_path / "evaluation_sample.json"
    report_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-03-11T03:05:00",
                "summary": {"primary_policy": "trained"},
                "policies": {
                    "trained": {"avg_reward": 12.0},
                    "random": {"avg_reward": 4.0},
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(api_fastapi, "ML_REPORTS_DIR", tmp_path)

    client = TestClient(api_fastapi.app)
    response = client.get("/ml-reports/evaluation_sample.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_name"] == "evaluation_sample.json"
    assert payload["report_type"] == "evaluation"
    assert payload["policies"]["trained"]["avg_reward"] == 12.0


def test_get_ml_report_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(api_fastapi, "ML_REPORTS_DIR", tmp_path)

    client = TestClient(api_fastapi.app)
    response = client.get("/ml-reports/../secrets.json")

    # FastAPI returns 404/400/HTTPException for invalid path segments or traversal depending on endpoint definition
    assert response.status_code in (404, 400)