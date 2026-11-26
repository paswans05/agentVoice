"""Tests for Phase 7 Leads Management, Consent, Suppression, Groups, and CSV Import/Export."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app()
    test_settings = Settings(app_env="test", data_dir=str(tmp_path))
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app)


def test_lead_crud_search_pagination_and_validation(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    # Invalid email/phone rejected
    assert client.post("/api/v1/leads", json={"full_name": "Bad", "email": "not-an-email"}).status_code == 422
    assert client.post("/api/v1/leads", json={"full_name": "Bad", "phone": "12"}).status_code == 422

    # Create 2 leads
    l1 = client.post(
        "/api/v1/leads",
        json={
            "first_name": "Rohan",
            "last_name": "Sharma",
            "email": "rohan@example.com",
            "phone": "+91 98765-43210",
            "company": "Acme India",
            "tags": ["vip"],
        },
    ).json()["data"]
    assert l1["consent_status"] == "UNKNOWN"
    assert l1["normalized_phone"] == "+919876543210"

    l2 = client.post(
        "/api/v1/leads",
        json={"full_name": "Priya Verma", "email": "priya@example.com", "status": "QUALIFIED"},
    ).json()["data"]

    # Search & filter
    res = client.get("/api/v1/leads?search=rohan&page=1&page_size=10").json()["data"]
    assert res["total"] == 1
    assert res["items"][0]["id"] == l1["id"]

    qual = client.get("/api/v1/leads?status=QUALIFIED").json()["data"]
    assert [i["id"] for i in qual["items"]] == [l2["id"]]

    # Stats
    stats = client.get("/api/v1/leads/stats").json()["data"]
    assert stats["total_leads"] == 2
    assert stats["qualified_leads"] == 1

    # Missing lead -> 404
    assert client.get("/api/v1/leads/lead_missing").status_code == 404


def test_consent_scoping_and_suppression_safeguards(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    lead = client.post(
        "/api/v1/leads",
        json={"full_name": "Amit", "phone": "+919988776655", "email": "amit@example.com"},
    ).json()["data"]
    lead_id = lead["id"]

    # Initially ineligible (UNKNOWN consent)
    elig0 = client.get(f"/api/v1/leads/{lead_id}/eligibility?channel=PHONE&purpose=SALES_CALLS").json()["data"]
    assert elig0["eligible"] is False
    assert elig0["applicable_consent_status"] == "UNKNOWN"

    # Grant EMAIL consent -> PHONE must still be blocked
    client.post(
        f"/api/v1/leads/{lead_id}/consent",
        json={"channel": "EMAIL", "purpose": "SALES_CALLS", "consent_status": "GRANTED", "source": "web_form"},
    )
    elig_phone = client.get(f"/api/v1/leads/{lead_id}/eligibility?channel=PHONE&purpose=SALES_CALLS").json()["data"]
    assert elig_phone["eligible"] is False

    # Grant PHONE consent -> now eligible
    client.post(
        f"/api/v1/leads/{lead_id}/consent",
        json={"channel": "PHONE", "purpose": "SALES_CALLS", "consent_status": "GRANTED", "source": "recorded_optin"},
    )
    elig_ok = client.get(f"/api/v1/leads/{lead_id}/eligibility?channel=PHONE&purpose=SALES_CALLS").json()["data"]
    assert elig_ok["eligible"] is True

    # Add suppression -> overrides eligibility & blocks status change away from DO_NOT_CONTACT
    sup = client.post(
        "/api/v1/suppression-list",
        json={"lead_id": lead_id, "reason": "Customer requested DNC"},
    ).json()["data"]
    elig_sup = client.get(f"/api/v1/leads/{lead_id}/eligibility?channel=PHONE&purpose=SALES_CALLS").json()["data"]
    assert elig_sup["eligible"] is False
    assert elig_sup["suppression_status"] is True

    bad_update = client.put(
        f"/api/v1/leads/{lead_id}",
        json={"full_name": "Amit", "status": "NEW"},
    )
    assert bad_update.status_code == 422

    # Deleting lead must NOT delete suppression record
    client.delete(f"/api/v1/leads/{lead_id}")
    sup_check = client.get(f"/api/v1/suppression-list/{sup['id']}")
    assert sup_check.status_code == 200


def test_csv_import_unicode_duplicates_and_formula_safe_export(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    # Pre-add suppression for blocked@example.com
    client.post(
        "/api/v1/suppression-list",
        json={"email": "blocked@example.com", "reason": "Opted out"},
    )

    csv_content = (
        "Name,Email,Phone,Notes\n"
        "राहुल कुमार,rahul@example.com,+919811122233,=SUM(A1:A2)\n"
        "Blocked User,blocked@example.com,+919800000000,Should be DNC\n"
        "Dup User,rahul@example.com,+919811122233,Duplicate\n"
        "Bad Email,invalid-email,+919822233344,Invalid\n"
    ).encode("utf-8")

    # 1. Preview
    prev = client.post(
        "/api/v1/leads/import/preview",
        files={"file": ("leads.csv", csv_content, "text/csv")},
    )
    assert prev.status_code == 200
    job_id = prev.json()["data"]["job_id"]
    mapping = prev.json()["data"]["suggested_mapping"]

    # 2. Execute
    exec_resp = client.post(
        "/api/v1/leads/import/execute",
        json={
            "job_id": job_id,
            "column_mapping": mapping,
            "duplicate_strategy": "SKIP",
            "match_strategy": "EMAIL_OR_PHONE",
        },
    )
    assert exec_resp.status_code == 200
    res = exec_resp.json()["data"]
    assert res["imported_count"] == 2
    assert res["duplicate_count"] == 1
    assert res["skipped_count"] == 1
    assert res["invalid_count"] == 1

    # Verify suppressed imported lead stayed DO_NOT_CONTACT and UNKNOWN consent
    blocked = client.get("/api/v1/leads?search=blocked").json()["data"]["items"][0]
    assert blocked["status"] == "DO_NOT_CONTACT"
    assert blocked["suppressed"] is True
    assert blocked["consent_status"] == "UNKNOWN"

    # 3. Export CSV & verify UTF-8 Unicode + formula injection protection
    # First create a lead with formula in company name
    client.post(
        "/api/v1/leads",
        json={"full_name": "अमित", "email": "amit2@example.com", "company": "=CMD()"},
    )
    exp = client.post("/api/v1/leads/export", json={"include_consent": True})
    assert exp.status_code == 200
    csv_text = exp.content.decode("utf-8-sig")
    assert "राहुल कुमार" in csv_text
    assert "'=CMD()" in csv_text


def test_groups_and_agent_assignment(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    agent = client.post("/api/v1/agents", json={"name": "Sales Bot", "type": "SALES"}).json()["data"]
    lead = client.post("/api/v1/leads", json={"full_name": "Neha"}).json()["data"]
    grp = client.post("/api/v1/lead-groups", json={"name": "Enterprise"}).json()["data"]

    # Add lead to group
    assert client.post(f"/api/v1/lead-groups/{grp['id']}/leads", json={"lead_ids": [lead["id"]]}).status_code == 200

    # Delete group must NOT delete lead
    assert client.delete(f"/api/v1/lead-groups/{grp['id']}").status_code == 200
    lead_after = client.get(f"/api/v1/leads/{lead['id']}").json()["data"]
    assert lead_after["group_ids"] == []

    # Assign valid agent
    assigned = client.post(f"/api/v1/leads/{lead['id']}/assign-agent?agent_id={agent['id']}")
    assert assigned.status_code == 200
    assert assigned.json()["data"]["assigned_agent_id"] == agent["id"]

    # Assign invalid agent -> 404
    assert client.post(f"/api/v1/leads/{lead['id']}/assign-agent?agent_id=agent_missing").status_code == 404

    # Activity timeline recorded
    acts = client.get(f"/api/v1/leads/{lead['id']}/activities").json()["data"]
    assert len(acts) >= 2
