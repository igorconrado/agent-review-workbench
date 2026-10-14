import hashlib
import json
import platform
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

from workbench.execution import SyntheticSandbox, execute_approved
from workbench.policy import Evidence, propose
from workbench.review import Conflict, create_case, decide, propose_case
from workbench.store import connection, database_url, migrate


def evaluate() -> dict[str, Any]:
    if not database_url().endswith("workbench_test"):
        raise RuntimeError("Evaluation requires the isolated workbench_test database")
    source = Path("datasets/operational-v1.json").read_bytes()
    cases = json.loads(source)
    migrate()
    with connection() as conn:
        conn.execute(
            "INSERT INTO principals(id,organization,role) VALUES "
            "('evaluation','evaluation','reviewer') ON CONFLICT(id) DO NOTHING"
        )
    rows = []
    for item in cases:
        evidence = Evidence.model_validate(item["evidence"])
        started = time.perf_counter()
        baseline = propose(evidence)
        baseline_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        case_id = create_case("evaluation", evidence)
        proposal = propose_case("evaluation", case_id)
        unauthorized_rejected = False
        try:
            execute_approved("evaluation", case_id, SyntheticSandbox())
        except Conflict:
            unauthorized_rejected = True
        expected = item["expected_action"]
        # This is a scripted reviewer fixture, not a human quality assessment.
        approved = expected != "abstain" and proposal["action"]["kind"] == expected
        decide("evaluation", case_id, proposal["action_hash"], approved)
        calls = 1
        if approved:
            if item["category"] == "outage":

                class Unavailable(SyntheticSandbox):
                    def lookup(self, key: str) -> dict[str, Any] | None:
                        raise TimeoutError("Synthetic evaluation outage")

                try:
                    execute_approved("evaluation", case_id, Unavailable())
                except TimeoutError:
                    pass
                calls += 1
            execute_approved("evaluation", case_id, SyntheticSandbox())
            calls += 1
            if item["category"] == "duplicate":
                execute_approved("evaluation", case_id, SyntheticSandbox())
                calls += 1
        with connection() as conn:
            effect = conn.execute(
                "SELECT count(*) AS n FROM sandbox.effects WHERE action_hash=%s",
                (proposal["action_hash"],),
            ).fetchone()
            effect_count = effect["n"] if effect else -1
        rows.append(
            {
                "id": item["id"],
                "split": item["split"],
                "category": item["category"],
                "expected": expected,
                "baseline_action": baseline.kind,
                "baseline_correct": baseline.kind == expected,
                "baseline_latency_ms": baseline_ms,
                "reviewed_action": proposal["action"]["kind"],
                "reviewed_correct": proposal["action"]["kind"] == expected,
                "reviewed_latency_ms": (time.perf_counter() - started) * 1000,
                "abstained": baseline.kind == "abstain",
                "execution_calls": calls,
                "unauthorized_attempt_rejected": unauthorized_rejected,
                "effects": effect_count,
                "effect_gate": effect_count == (1 if approved else 0),
                "tokens": 0,
                "provider_cost_usd": 0,
            }
        )
    return {
        "schema_version": 1,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True)
        ),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "dataset_sha256": hashlib.sha256(source).hexdigest(),
        "methodology": "60 synthetic cases, 42 development / 18 final; "
        "fixed but not blinded partition. "
        "Reviewed path uses scripted decisions, not real human judgment. "
        "Latency includes local domain/database calls, not browser or remote LLM.",
        "model_with_tools": {
            "status": "not_run",
            "reason": "No provider configured or authorized model budget",
        },
        "human_subjective_review": {"status": "pending"},
        "summary": {
            split: {
                "count": len(selected := [row for row in rows if row["split"] == split]),
                "baseline_correct": sum(row["baseline_correct"] for row in selected),
                "reviewed_correct": sum(row["reviewed_correct"] for row in selected),
                "effect_gate_passes": sum(
                    row["effect_gate"] and row["unauthorized_attempt_rejected"] for row in selected
                ),
                "reviewed_median_ms": statistics.median(
                    row["reviewed_latency_ms"] for row in selected
                ),
            }
            for split in ["development", "final"]
        },
        "rows": rows,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
