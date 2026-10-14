"""The sandbox commits independently; checkpoints never determine whether an effect exists."""

from collections.abc import Callable
from typing import Any, Protocol
from uuid import UUID

from psycopg.types.json import Jsonb

from workbench.policy import Action, action_hash
from workbench.review import Conflict, audit, locked_case
from workbench.store import connection


class Gateway(Protocol):
    def lookup(self, key: str) -> dict[str, Any] | None: ...
    def execute(self, key: str, action: Action) -> dict[str, Any]: ...


class SyntheticSandbox:
    """Separate transaction models a provider with authoritative idempotency lookup."""

    def lookup(self, key: str) -> dict[str, Any] | None:
        with connection() as conn:
            row = conn.execute(
                "SELECT result FROM sandbox.effects WHERE action_hash=%s", (key,)
            ).fetchone()
            return dict(row["result"]) if row else None

    def execute(self, key: str, action: Action) -> dict[str, Any]:
        result = {"effect_id": key, "kind": action.kind, "sandbox_only": True}
        with connection() as conn:
            conn.execute(
                "INSERT INTO sandbox.effects(action_hash,action,result) VALUES (%s,%s,%s) "
                "ON CONFLICT(action_hash) DO NOTHING",
                (key, Jsonb(action.model_dump()), Jsonb(result)),
            )
            row = conn.execute(
                "SELECT action,result FROM sandbox.effects WHERE action_hash=%s", (key,)
            ).fetchone()
            if not row or row["action"] != action.model_dump():
                raise Conflict("Provider idempotency payload conflict")
            return dict(row["result"])


def execute_approved(
    principal_id: str,
    case_id: str,
    gateway: Gateway,
    after_effect: Callable[[], None] | None = None,
) -> dict[str, Any]:
    with connection() as conn:
        case = locked_case(conn, principal_id, case_id)
        if case["status"] not in {"approved", "uncertain", "executed", "cancelled"}:
            raise Conflict("No executable approval")
        action = Action.model_validate(case["action"])
        key = action_hash(case_id, case["context_version"], action)
        if key != case["action_hash"] or not case["decision_by"] or action.kind == "abstain":
            raise Conflict("Approval does not match the current action")
        if (
            case["status"] == "cancelled"
            and not conn.execute("SELECT 1 FROM tool_calls WHERE action_hash=%s", (key,)).fetchone()
        ):
            raise Conflict("Cancelled action has no previous attempt to reconcile")
        conn.execute(
            "INSERT INTO tool_calls(action_hash,case_id,state) VALUES (%s,%s,'unknown') "
            "ON CONFLICT(action_hash) DO NOTHING",
            (key, UUID(case_id)),
        )
        if case["status"] not in {"executed", "cancelled"}:
            conn.execute("UPDATE cases SET status='uncertain' WHERE id=%s", (UUID(case_id),))

    # The durable unknown record precedes the external call. A process death here
    # leaves recoverable work. The case lock serializes context/cancellation/effect decisions.
    with connection() as conn:
        case = locked_case(conn, principal_id, case_id)
        call = conn.execute("SELECT * FROM tool_calls WHERE action_hash=%s", (key,)).fetchone()
        if not call:
            raise Conflict("Missing execution journal")
        if call["state"] == "settled":
            return dict(call["result"])
        result = gateway.lookup(key)
        if result is None:
            if case["status"] != "uncertain" or case["action_hash"] != key:
                raise Conflict("Cancelled or superseded action cannot start a new effect")
            result = gateway.execute(key, action)
        if after_effect:
            after_effect()
        conn.execute(
            "UPDATE tool_calls SET state='settled',result=%s WHERE action_hash=%s",
            (Jsonb(result), key),
        )
        if case["status"] != "cancelled":
            conn.execute("UPDATE cases SET status='executed' WHERE id=%s", (UUID(case_id),))
        audit(conn, case_id, principal_id, "effect_verified")
        return result
