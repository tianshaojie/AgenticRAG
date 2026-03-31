from __future__ import annotations

import pytest


@pytest.mark.integration
def test_eval_run_and_fetch_endpoints(client) -> None:
    run_resp = client.post(
        "/evals/run",
        json={
            "dataset": "golden_v1",
            "name": "api-eval-run",
            "config": {},
        },
    )
    assert run_resp.status_code == 200
    run_payload = run_resp.json()
    assert run_payload["accepted"] is True
    assert run_payload["status"] == "succeeded"
    assert run_payload["summary"]["gate_passed"] is True

    eval_run_id = run_payload["eval_run_id"]
    get_resp = client.get(f"/evals/{eval_run_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["eval_run_id"] == eval_run_id
    assert detail["dataset"] == "golden_v1"
    assert detail["summary"]["total_cases"] >= 1


@pytest.mark.integration
def test_eval_latest_endpoint(client) -> None:
    run_resp = client.post(
        "/evals/run",
        json={
            "dataset": "golden_v1",
            "name": "api-eval-latest",
            "config": {},
        },
    )
    assert run_resp.status_code == 200

    latest = client.get("/evals/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["name"] in {"api-eval-latest", "api-eval-run"}
    assert "summary" in payload
