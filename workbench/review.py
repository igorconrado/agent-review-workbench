from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from workbench.policy import Evidence, action_hash, propose
from workbench.store import connection


class Conflict(Exception):
    pass


class Forbidden(Exception):
    pass


def authorize(conn: Any, principal_id: str, organization: str, mutate: bool = True) -> None:
    principal = conn.execute(
        "SELECT * FROM principals WHERE id=%s FOR SHARE", (principal_id,)
    ).fetchone()
    if (
        not principal
        or not principal["active"]
        or principal["organization"] != organization
        or (mutate and principal["role"] != "reviewer")
    ):
        raise Forbidden("Current principal is not authorized")


def locked_case(conn: Any, principal_id: str, case_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM cases WHERE id=%s FOR UPDATE", (UUID(case_id),)).fetchone()
    if not row:
        raise Forbidden("Case unavailable")
    authorize(conn, principal_id, row["organization"])
    return dict(row)


def audit(conn: Any, case_id: str, principal_id: str, event: str) -> None:
    conn.execute(
        "INSERT INTO audit(case_id,actor,event) VALUES (%s,%s,%s)",
        (UUID(case_id), principal_id, event),
    )


def create_case(principal_id: str, evidence: Evidence) -> str:
    with connection() as conn:
        principal = conn.execute("SELECT * FROM principals WHERE id=%s", (principal_id,)).fetchone()
        if not principal:
            raise Forbidden("Unknown principal")
        authorize(conn, principal_id, principal["organization"])
        case_id = str(uuid4())
        conn.execute(
            "INSERT INTO cases(id,organization,evidence) VALUES (%s,%s,%s)",
            (UUID(case_id), principal["organization"], Jsonb(evidence.model_dump())),
        )
        audit(conn, case_id, principal_id, "created")
        return case_id


def propose_case(principal_id: str, case_id: str) -> dict[str, Any]:
    with connection() as conn:
        case = locked_case(conn, principal_id, case_id)
        if case["status"] not in {"open", "review"}:
            raise Conflict("Case no longer accepts proposals")
        action = propose(Evidence.model_validate(case["evidence"]))
        digest = action_hash(case_id, case["context_version"], action)
        conn.execute(
            "UPDATE cases SET action=%s,action_hash=%s,status='review' WHERE id=%s",
            (Jsonb(action.model_dump()), digest, UUID(case_id)),
        )
        audit(conn, case_id, principal_id, "proposed")
        return {
            "action": action.model_dump(),
            "action_hash": digest,
            "context_version": case["context_version"],
        }


def decide(principal_id: str, case_id: str, digest: str, approve: bool) -> None:
    with connection() as conn:
        case = locked_case(conn, principal_id, case_id)
        if case["status"] != "review" or case["action_hash"] != digest:
            raise Conflict("Decision is stale or already recorded")
        if approve and case["action"]["kind"] == "abstain":
            raise Conflict("Abstention cannot authorize an effect")
        status = "approved" if approve else "rejected"
        conn.execute(
            "UPDATE cases SET status=%s,decision_by=%s WHERE id=%s",
            (status, principal_id, UUID(case_id)),
        )
        audit(conn, case_id, principal_id, status)


def replace_evidence(principal_id: str, case_id: str, evidence: Evidence) -> None:
    with connection() as conn:
        case = locked_case(conn, principal_id, case_id)
        if case["status"] in {"executed", "uncertain", "cancelled"}:
            raise Conflict("Reconcile completed or uncertain work before changing context")
        conn.execute(
            "UPDATE cases SET evidence=%s,context_version=context_version+1,"
            "action=NULL,action_hash=NULL,decision_by=NULL,status='open' WHERE id=%s",
            (Jsonb(evidence.model_dump()), UUID(case_id)),
        )
        audit(conn, case_id, principal_id, "context_replaced")


def cancel(principal_id: str, case_id: str) -> dict[str, Any]:
    with connection() as conn:
        locked_case(conn, principal_id, case_id)
        calls = conn.execute(
            "SELECT state,result FROM tool_calls WHERE case_id=%s", (UUID(case_id),)
        ).fetchall()
        conn.execute("UPDATE cases SET status='cancelled' WHERE id=%s", (UUID(case_id),))
        audit(conn, case_id, principal_id, "cancelled")
        return {
            "status": "cancelled",
            "effects": [row["result"] for row in calls if row["state"] == "settled"],
            "reconciliation_required": any(row["state"] == "unknown" for row in calls),
        }
