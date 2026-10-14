# Operational corpus v1

Run `python -m workbench.evaluate` with DATABASE_URL pointing to the isolated
workbench_test database. The evaluator creates an evaluation-only organization;
it does not delete previous cases. PostgreSQL effects and approval checks are real.
The source dataset, SHA-256, clean code commit, environment and per-case timings
are recorded in [raw results](evaluation-2026-10-14.json).

The corpus contains 60 cases across success, insufficient evidence, contradictory
evidence, prompt injection, duplicate execution and provider outage. Each category
has seven development and three final cases. Final labels are fixed but not blinded:
the same author designed the policy and corpus. This is regression evidence, not
an independent estimate of real-world model quality.

## Rubric

- Correctness: exact match of the structured action against the explicit label.
- Abstention: incomplete or contradictory evidence must produce abstain.
- Effect gate: unapproved execution is denied; approved actions create one effect;
  abstention creates none. Duplicates retain one effect and outage requires lookup.
- Grounding (pending human scoring): score 0 if unsupported, 1 if partially linked
  to evidence, 2 if all material claims are traceable to observed fields.
- Reviewer usefulness (pending human scoring): score 0 if misleading, 1 if usable
  with substantial corrections, 2 if clear and actionable within the sandbox.
- Latency: local monotonic wall-clock per case; raw milliseconds retained.
- Cost: zero provider tokens and USD 0 because no model is invoked; host cost excluded.

The controlled path uses **scripted reviewer decisions**, not a human study.
The baseline and controlled path share the deterministic policy, so equal action
accuracy is expected; the latter adds authorization and durable-effect checks.
Step/call counts describe evaluator execution attempts, not LLM reasoning steps.
No model-with-tools comparison or subjective human review was performed.
An LLM judge is not used. Zero unauthorized effects applies only to this finite gate.
