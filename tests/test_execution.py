import os
import subprocess
import sys

import pytest

from tests.test_review import database, new_case  # noqa: F401
from workbench.execution import SyntheticSandbox, execute_approved
from workbench.review import Conflict, Forbidden, cancel, decide, propose_case
from workbench.store import connection

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Real PostgreSQL required")


def approved():
    case_id = new_case()
    proposal = propose_case("ana", case_id)
    decide("ana", case_id, proposal["action_hash"], True)
    return case_id


def test_execution_retries_return_one_effect():
    case_id = approved()
    first = execute_approved("ana", case_id, SyntheticSandbox())
    assert execute_approved("ana", case_id, SyntheticSandbox()) == first
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 1


def test_process_death_after_effect_reconciles_without_duplicate():
    case_id = approved()
    script = (
        "import os; from workbench.execution import execute_approved,SyntheticSandbox; "
        f"execute_approved('ana','{case_id}',SyntheticSandbox(),lambda: os._exit(86))"
    )
    result = subprocess.run([sys.executable, "-c", script], check=False, timeout=15)
    assert result.returncode == 86
    with connection() as conn:
        assert conn.execute("SELECT state FROM tool_calls").fetchone()["state"] == "unknown"
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 1
    execute_approved("ana", case_id, SyntheticSandbox())
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 1
        assert conn.execute("SELECT state FROM tool_calls").fetchone()["state"] == "settled"


def test_revocation_before_execution_prevents_effect():
    case_id = approved()
    with connection() as conn:
        conn.execute("UPDATE principals SET role='viewer' WHERE id='ana'")
    with pytest.raises(Forbidden):
        execute_approved("ana", case_id, SyntheticSandbox())
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 0


@pytest.mark.parametrize("revocation", ["active=false", "role='viewer'", "organization='cedro'"])
def test_another_reviewer_cannot_execute_a_revoked_approval(revocation):
    case_id = approved()
    with connection() as conn:
        conn.execute(f"UPDATE principals SET {revocation} WHERE id='ana'")
    with pytest.raises(Forbidden):
        execute_approved("bia", case_id, SyntheticSandbox())
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 0


def test_authorized_reviewer_can_reconcile_existing_effect_after_approver_revocation():
    case_id = approved()

    def lost_response():
        raise TimeoutError("Effect committed before response loss")

    with pytest.raises(TimeoutError):
        execute_approved("ana", case_id, SyntheticSandbox(), lost_response)
    with connection() as conn:
        conn.execute("UPDATE principals SET active=false WHERE id='ana'")
    result = execute_approved("bia", case_id, SyntheticSandbox())
    assert result["sandbox_only"] is True
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 1
        assert conn.execute("SELECT state FROM tool_calls").fetchone()["state"] == "settled"


def test_cancelled_approval_cannot_execute():
    case_id = approved()
    cancel("ana", case_id)
    with pytest.raises(Conflict):
        execute_approved("ana", case_id, SyntheticSandbox())


def test_provider_unavailable_keeps_unknown_journal():
    class Unavailable(SyntheticSandbox):
        def lookup(self, key):
            raise TimeoutError("Synthetic provider unavailable")

    case_id = approved()
    with pytest.raises(TimeoutError):
        execute_approved("ana", case_id, Unavailable())
    with connection() as conn:
        assert conn.execute("SELECT state FROM tool_calls").fetchone()["state"] == "unknown"
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 0
    execute_approved("ana", case_id, SyntheticSandbox())


def test_cancel_unknown_prevents_new_effect_but_reports_uncertainty():
    class Unavailable(SyntheticSandbox):
        def lookup(self, key):
            raise TimeoutError("Unavailable")

    case_id = approved()
    with pytest.raises(TimeoutError):
        execute_approved("ana", case_id, Unavailable())
    assert cancel("ana", case_id)["reconciliation_required"] is True
    with pytest.raises(Conflict):
        execute_approved("ana", case_id, SyntheticSandbox())
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 0


def test_cancel_reports_completed_effect():
    case_id = approved()
    result = execute_approved("ana", case_id, SyntheticSandbox())
    assert cancel("ana", case_id)["effects"] == [result]
