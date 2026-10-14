import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.test_review import database, new_case  # noqa: F401
from workbench.graph import run_graph
from workbench.policy import Action, Evidence
from workbench.review import Conflict, Forbidden, decide, edit_proposal, replace_evidence
from workbench.store import connection

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Real PostgreSQL required")


def test_checkpoint_survives_process_restart_and_requires_domain_approval():
    case_id = new_case()
    process = subprocess.run(
        [
            sys.executable,
            "-c",
            f"from workbench.graph import run_graph; run_graph('ana','{case_id}')",
        ],
        timeout=30,
        check=False,
    )
    assert process.returncode == 0
    with pytest.raises(Conflict):
        run_graph("ana", case_id, resume=True)
    with connection() as conn:
        digest = conn.execute("SELECT action_hash FROM cases WHERE id=%s", (case_id,)).fetchone()[
            "action_hash"
        ]
    decide("ana", case_id, digest, True)
    result = run_graph("ana", case_id, resume=True)
    assert result["result"]["sandbox_only"] is True
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 1


def test_cross_tenant_cannot_read_or_resume_checkpoint():
    case_id = new_case()
    run_graph("ana", case_id)
    with pytest.raises(Forbidden):
        run_graph("cedro", case_id, resume=True)


def test_resume_executes_current_reviewed_edit_instead_of_checkpoint_proposal():
    case_id = new_case()
    old = run_graph("ana", case_id)["proposal"]
    digest = edit_proposal(
        "ana",
        case_id,
        old["action_hash"],
        Action(
            kind="close_no_action",
            reason="Reviewer checked the synthetic evidence",
        ),
    )
    decide("ana", case_id, digest, True)
    result = run_graph("ana", case_id, resume=True)
    assert result["result"]["kind"] == "close_no_action"


def test_replaced_context_requires_new_proposal_and_concurrent_resumes_keep_one_effect():
    case_id = new_case()
    old = run_graph("ana", case_id)["proposal"]
    replace_evidence(
        "ana",
        case_id,
        Evidence(
            order_status="confirmed",
            payment_status="paid",
            amount_cents=1200,
        ),
    )
    with pytest.raises(Conflict):
        decide("ana", case_id, old["action_hash"], True)
    with pytest.raises(Conflict):
        run_graph("ana", case_id, resume=True)
    current = run_graph("ana", case_id)["proposal"]
    assert current["context_version"] == 2
    decide("ana", case_id, current["action_hash"], True)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: run_graph("ana", case_id, resume=True), range(2)))
    assert all(result["result"]["kind"] == "close_no_action" for result in results)
    with connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM sandbox.effects").fetchone()["n"] == 1
