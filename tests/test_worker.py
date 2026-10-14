import os

import pytest

from tests.test_review import database, new_case  # noqa: F401
from workbench.graph import run_graph
from workbench.review import Conflict, Forbidden, decide, propose_case
from workbench.store import connection
from workbench.worker import retry_case, tick

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Real PostgreSQL required")


def test_worker_resumes_approved_case_and_repeated_tick_does_not_duplicate():
    case_id = new_case()
    proposal = run_graph("ana", case_id)["proposal"]
    decide("ana", case_id, proposal["action_hash"], True)
    tick()
    tick()
    with connection() as conn:
        assert (
            conn.execute("SELECT status FROM cases WHERE id=%s", (case_id,)).fetchone()["status"]
            == "executed"
        )
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 1


def test_worker_preserves_pending_work_when_reviewer_is_revoked(capsys):
    case_id = new_case()
    proposal = run_graph("ana", case_id)["proposal"]
    decide("ana", case_id, proposal["action_hash"], True)
    with connection() as conn:
        conn.execute("UPDATE principals SET active=false WHERE id='ana'")
    tick()
    assert '"event": "worker_failed"' in capsys.readouterr().out
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 0
        assert (
            conn.execute("SELECT status FROM cases WHERE id=%s", (case_id,)).fetchone()["status"]
            == "approved"
        )


def test_failed_batch_does_not_starve_later_approved_work():
    cases = []
    for index in range(21):
        case_id = new_case()
        proposal = propose_case("ana", case_id)
        decide("bia" if index == 20 else "ana", case_id, proposal["action_hash"], True)
        cases.append(case_id)
    with connection() as conn:
        conn.execute("UPDATE principals SET active=false WHERE id='ana'")
    tick()
    tick()
    with connection() as conn:
        assert (
            conn.execute("SELECT status FROM cases WHERE id=%s", (cases[-1],)).fetchone()["status"]
            == "executed"
        )
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 1


def test_worker_budget_is_durable_and_replay_is_authorized():
    case_id = new_case()
    proposal = propose_case("ana", case_id)
    decide("ana", case_id, proposal["action_hash"], True)
    with connection() as conn:
        conn.execute("UPDATE principals SET active=false WHERE id='ana'")
    for _ in range(5):
        with connection() as conn:
            conn.execute("UPDATE cases SET worker_available_at=now() WHERE id=%s", (case_id,))
        tick()
    with connection() as conn:
        conn.execute("UPDATE cases SET worker_available_at=now() WHERE id=%s", (case_id,))
    tick()
    with connection() as conn:
        row = conn.execute(
            "SELECT worker_attempts,worker_last_error FROM cases WHERE id=%s", (case_id,)
        ).fetchone()
        assert row == {"worker_attempts": 5, "worker_last_error": "Forbidden"}
    for actor in ["viewer", "cedro"]:
        with pytest.raises(Forbidden):
            retry_case(actor, case_id)
    retry_case("bia", case_id)
    with pytest.raises(Conflict):
        retry_case("bia", case_id)
    with connection() as conn:
        conn.execute("UPDATE principals SET active=true WHERE id='ana'")
    tick()
    with connection() as conn:
        assert (
            conn.execute("SELECT status FROM cases WHERE id=%s", (case_id,)).fetchone()["status"]
            == "executed"
        )
        assert (
            conn.execute(
                "SELECT count(*) AS n FROM audit WHERE event='worker_retry_requested'"
            ).fetchone()["n"]
            == 1
        )
