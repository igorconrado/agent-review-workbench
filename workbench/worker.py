"""Single-process demonstration worker; PostgreSQL remains authoritative."""

import json
import time

from workbench.execution import SyntheticSandbox, execute_approved
from workbench.review import Conflict, audit, locked_case
from workbench.store import connection


def tick() -> None:
    with connection() as conn:
        pending = conn.execute(
            "WITH due AS (SELECT id FROM cases WHERE status IN ('approved','uncertain') "
            "AND worker_attempts<5 AND worker_available_at<=clock_timestamp() "
            "ORDER BY worker_available_at,created_at,id LIMIT 20 FOR UPDATE SKIP LOCKED) "
            "UPDATE cases SET worker_available_at=clock_timestamp()+"
            "interval '5 seconds' * power(2,worker_attempts), "
            "worker_attempts=worker_attempts+1 FROM due WHERE cases.id=due.id "
            "RETURNING cases.id,cases.decision_by"
        ).fetchall()
    for case in pending:
        case_id = str(case["id"])
        try:
            execute_approved(case["decision_by"], case_id, SyntheticSandbox())
            with connection() as conn:
                conn.execute("UPDATE cases SET worker_last_error=NULL WHERE id=%s", (case_id,))
            print(json.dumps({"event": "worker_completed", "case_id": case_id}), flush=True)
        except Exception as error:
            with connection() as conn:
                conn.execute(
                    "UPDATE cases SET worker_last_error=%s WHERE id=%s",
                    (type(error).__name__, case_id),
                )
            print(
                json.dumps(
                    {
                        "event": "worker_failed",
                        "case_id": case_id,
                        "error_type": type(error).__name__,
                    }
                ),
                flush=True,
            )


def retry_case(principal_id: str, case_id: str) -> None:
    with connection() as conn:
        case = locked_case(conn, principal_id, case_id)
        if case["status"] not in {"approved", "uncertain"} or case["worker_attempts"] < 5:
            raise Conflict("Only exhausted pending work can be retried")
        conn.execute(
            "UPDATE cases SET worker_attempts=0,worker_available_at=clock_timestamp(),"
            "worker_last_error=NULL WHERE id=%s",
            (case_id,),
        )
        audit(conn, case_id, principal_id, "worker_retry_requested")


if __name__ == "__main__":
    while True:
        tick()
        time.sleep(5)
