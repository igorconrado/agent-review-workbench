import os

import pytest
from fastapi.testclient import TestClient

from tests.test_review import database  # noqa: F401
from workbench.api import app
from workbench.execution import SyntheticSandbox, execute_approved
from workbench.identity import seed
from workbench.store import connection

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Real PostgreSQL required")
origin = {"origin": "http://127.0.0.1:3200"}


def signed_in(name="ana"):
    seed()
    client = TestClient(app, headers=origin)
    response = client.post(
        "/api/session",
        json={
            "principal_id": name,
            "password": "Synthetic-Test-Password",
        },
    )
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    return client


def test_authenticated_review_to_effect_and_logout():
    with signed_in() as client:
        response = client.post(
            "/api/cases",
            json={
                "order_status": "expired",
                "payment_status": "paid",
                "amount_cents": 100,
            },
        )
        assert response.status_code == 201
        case_id = response.json()["case_id"]
        assert client.post(f"/api/cases/{case_id}/execute").status_code == 409
        proposal = client.post(f"/api/cases/{case_id}/propose").json()
        assert (
            client.post(
                f"/api/cases/{case_id}/decision",
                json={
                    "action_hash": proposal["action_hash"],
                    "approve": True,
                },
            ).status_code
            == 200
        )
        result = client.post(f"/api/cases/{case_id}/execute")
        assert result.status_code == 200
        assert result.json()["sandbox_only"]
        assert client.delete("/api/session").status_code == 200
        assert client.get("/api/cases").status_code == 403


def test_origin_role_and_tenant_enforced():
    with signed_in() as owner:
        case_id = owner.post(
            "/api/cases",
            json={
                "order_status": "expired",
                "payment_status": "paid",
                "amount_cents": 100,
            },
        ).json()["case_id"]
        assert (
            owner.post(
                f"/api/cases/{case_id}/propose", headers={"origin": "https://evil.test"}
            ).status_code
            == 403
        )
    with signed_in("cedro") as other:
        assert other.get("/api/cases").json()["cases"] == []
        assert other.post(f"/api/cases/{case_id}/propose").status_code == 403
    with signed_in("viewer") as viewer:
        assert viewer.get("/api/cases").status_code == 200
        assert viewer.post(f"/api/cases/{case_id}/propose").status_code == 403


def test_session_revocation_takes_effect_immediately():
    with signed_in() as client:
        with connection() as conn:
            conn.execute("UPDATE principals SET active=false WHERE id='ana'")
        assert client.get("/api/cases").status_code == 403


def test_cancelled_unknown_result_can_be_verified_through_api():
    class Unavailable(SyntheticSandbox):
        def lookup(self, key):
            raise TimeoutError("Unavailable")

    with signed_in() as client:
        case_id = client.post(
            "/api/cases",
            json={
                "order_status": "expired",
                "payment_status": "paid",
                "amount_cents": 100,
            },
        ).json()["case_id"]
        proposal = client.post(f"/api/cases/{case_id}/propose").json()
        client.post(
            f"/api/cases/{case_id}/decision",
            json={
                "action_hash": proposal["action_hash"],
                "approve": True,
            },
        )
        assert client.post(f"/api/cases/{case_id}/reconcile").status_code == 409
        with pytest.raises(TimeoutError):
            execute_approved("ana", case_id, Unavailable())
        assert client.post(f"/api/cases/{case_id}/cancel").json()["reconciliation_required"]
        assert client.get("/api/cases").json()["cases"][0]["reconciliation_required"]
        response = client.post(f"/api/cases/{case_id}/reconcile")
        assert response.status_code == 200
        assert response.json()["outcome"] == "not_applied"
        row = client.get("/api/cases").json()["cases"][0]
        assert row["status"] == "cancelled"
        assert row["reconciliation_required"] is False
    for name in ["viewer", "cedro"]:
        with signed_in(name) as denied:
            assert denied.post(f"/api/cases/{case_id}/reconcile").status_code == 403
