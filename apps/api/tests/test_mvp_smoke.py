from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def test_mvp_smoke_flow():
    client = TestClient(app)

    scan_response = client.post(
        "/projects/scan",
        json={"root_path": str(FIXTURE), "extra_ignore_patterns": []},
    )
    assert scan_response.status_code == 200
    scan = scan_response.json()
    assert scan["docs"] == ["README.md"]
    assert scan["tests"] == ["tests/test_app.py"]

    project_response = client.post(
        "/projects",
        json={"root_path": str(FIXTURE), "extra_ignore_patterns": [], "name": "Smoke Sample Project"},
    )
    assert project_response.status_code == 200
    project = project_response.json()
    assert project["slug"] == "smoke-sample-project"

    playbook_response = client.post("/playbooks/distill", json={"project_id": project["id"]})
    assert playbook_response.status_code == 200
    playbook = playbook_response.json()
    assert playbook["project_id"] == project["id"]

    review_response = client.post(
        "/reviews",
        json={
            "playbook_id": playbook["id"],
            "proposal": (
                "Add a background indexing worker for project ingestion, keep the API layer thin, "
                "touch only the ingestion module, and validate the change with existing pytest coverage."
            ),
            "mode": "standard",
        },
    )
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["playbook_id"] == playbook["id"]
    assert review["overall_judgement"] in {"通过", "有条件通过", "建议修改后再评审", "不建议采用"}
    assert isinstance(review["key_risks"], list)
    assert isinstance(review["playbook_conflicts"], list)
    assert isinstance(review["suggested_changes"], list)
    assert isinstance(review["required_validation"], list)
    assert isinstance(review["missing_information"], list)
    assert "id" in review
