import os

import pytest

from tests.test_review import database, new_case  # noqa: F401
from workbench.graph import run_graph
from workbench.review import decide
from workbench.store import connection
from workbench.worker import tick

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
