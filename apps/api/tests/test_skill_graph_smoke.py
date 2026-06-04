from fastapi.testclient import TestClient

from app.main import app


def test_skill_graph_sample_smoke_flow():
    client = TestClient(app)

    playbooks = client.get("/graph/playbooks")
    assert playbooks.status_code == 200
    assert any(item["id"] == "graph_weekly_competitor_report" for item in playbooks.json())

    compile_response = client.post("/graph/playbooks/graph_weekly_competitor_report/compile")
    assert compile_response.status_code == 200
    assert compile_response.json()["ok"] is True

    run_response = client.post(
        "/graph/playbooks/graph_weekly_competitor_report/runs",
        json={"input_payload": {"competitor": "Acme"}},
    )
    assert run_response.status_code == 200
    run_body = run_response.json()
    assert run_body["status"] == "waiting_for_human"

    approval_response = client.post(
        f"/graph/runs/{run_body['id']}/approvals/{run_body['approvals'][0]['approval_id']}",
        json={"approved": True, "decided_by": "smoke-test"},
    )
    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "succeeded"
