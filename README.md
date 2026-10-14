# Agent Review Workbench

A synthetic operational-exception review system under active implementation.
It is an independent portfolio project, not a reconstruction of an employer's system.

## Current evidence

Implemented: strict structured evidence, deterministic proposal or abstention,
action/context digests, PostgreSQL review decisions with row locks, tenant and
current-role authorization, context invalidation and cancellation.

Not yet implemented: usable browser flow, authenticated API sessions, external
sandbox execution/reconciliation, LangGraph runtime/checkpoints, MCP transport,
60-case evaluation dataset, model comparison, backup and deployment.
Installed dependencies do not constitute evidence of those capabilities.

## Run checks

Use Python 3.13 and Node 24. Create a virtual environment and install
`pip install -r requirements-lock.txt`. Run `npm ci`, then `npm run db:test`
in a separate terminal for an independent native PostgreSQL 18.4 database.
The embedded development launcher package is prerelease; CI uses the official
PostgreSQL image. The synthetic local connection is
`postgresql://workbench:local-synthetic-only@127.0.0.1:55443/workbench_test`.

Set `DATABASE_URL` to that value and run:

```sh
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest -q
python -m pip_audit --disable-pip --no-deps -r requirements-lock.txt
```

Integration fixtures erase only a database whose URL ends with `workbench_test`.
Do not point them at persistent user data. Without DATABASE_URL, PostgreSQL tests
skip explicitly. These tests do not prove a complete review-to-effect workflow.
