import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from workbench.policy import Evidence
from workbench.review import (
    Conflict,
    Forbidden,
    cancel,
    create_case,
    decide,
    propose_case,
    replace_evidence,
)
from workbench.store import connection, migrate

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Real PostgreSQL required")


@pytest.fixture(autouse=True)
def database():
    if not os.environ["DATABASE_URL"].endswith("workbench_test"):
        raise RuntimeError("Destructive integration fixture requires workbench_test")
    migrate()
    with connection() as conn:
        conn.execute("TRUNCATE audit,tool_calls,cases,principals,sandbox.effects CASCADE")
        conn.execute(
            "INSERT INTO principals(id,organization,role) VALUES "
            "('ana','aurora','reviewer'),('bia','aurora','reviewer'),"
            "('viewer','aurora','viewer'),('cedro','cedro','reviewer')"
        )


def new_case():
    return create_case(
        "ana", Evidence(order_status="expired", payment_status="paid", amount_cents=1200)
    )


def test_concurrent_decisions_have_one_winner():
    case_id = new_case()
    proposal = propose_case("ana", case_id)

    def decision(actor):
        try:
            decide(actor, case_id, proposal["action_hash"], actor == "ana")
            return "accepted"
        except Conflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(decision, ["ana", "bia"])) == ["accepted", "conflict"]


def test_context_replacement_invalidates_approval():
    case_id = new_case()
    proposal = propose_case("ana", case_id)
    decide("ana", case_id, proposal["action_hash"], True)
    replace_evidence(
        "ana", case_id, Evidence(order_status="confirmed", payment_status="paid", amount_cents=1200)
    )
    with pytest.raises(Conflict):
        decide("ana", case_id, proposal["action_hash"], True)
    updated = propose_case("ana", case_id)
    assert updated["context_version"] == 2
    assert updated["action_hash"] != proposal["action_hash"]


@pytest.mark.parametrize("actor", ["viewer", "cedro", "unknown"])
def test_unauthorized_principal_cannot_propose(actor):
    with pytest.raises(Forbidden):
        propose_case(actor, new_case())


def test_role_revocation_rechecked_at_decision():
    case_id = new_case()
    proposal = propose_case("ana", case_id)
    with connection() as conn:
        conn.execute("UPDATE principals SET active=false WHERE id='ana'")
    with pytest.raises(Forbidden):
        decide("ana", case_id, proposal["action_hash"], True)


def test_cancel_blocks_subsequent_proposal_and_approval():
    case_id = new_case()
    proposal = propose_case("ana", case_id)
    cancel("ana", case_id)
    with pytest.raises(Conflict):
        propose_case("ana", case_id)
    with pytest.raises(Conflict):
        decide("ana", case_id, proposal["action_hash"], True)
