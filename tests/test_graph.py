import os
import subprocess
import sys

import pytest

from tests.test_review import database, new_case  # noqa: F401
from workbench.graph import run_graph
from workbench.review import Conflict, Forbidden, decide
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
