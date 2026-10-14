# Agent Review Workbench

A synthetic operational-exception review system under active implementation.
It is an independent portfolio project, not a reconstruction of an employer's system.

## Current evidence

Implemented: strict structured evidence, deterministic proposal or abstention,
action/context digests, PostgreSQL review decisions with row locks, tenant and
current-role authorization, context invalidation and cancellation. A durable
execution journal reconciles sandbox effects by stable action hash after process
death. The sandbox commits in an independent transaction/schema on the same
PostgreSQL server: it models provider semantics, not network or host isolation.

Not yet implemented: usable browser flow, authenticated API sessions, external
HTTP sandbox transport, 60-case evaluation dataset, model comparison, backup and deployment.
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
skip explicitly. The domain review-to-effect flow is tested; a usable authenticated
browser/API flow is still pending.

## Verified failure boundary

The integration suite starts a child Python process, commits the independent
sandbox effect, then exits with code 86 before committing the local result.
The next invocation finds the effect by its durable key and settles the journal.
One provider effect remains. Unavailable lookup leaves the journal unknown and
does not trigger a blind retry. Cancellation blocks new effects, reports known
effects, and preserves unresolved uncertainty. Authorization is reloaded at execution.

Local validation on 2026-10-14: 24 tests passed, including real PostgreSQL and the
process-death scenario. The initial decision slice also passed clean Linux CI:
[run 38646754031](https://github.com/igorconrado/agent-review-workbench/actions/runs/38646754031).
This bounded test gate is not a universal claim of agent safety.

## Checkpoints and restricted tools

`workbench/graph.py` runs three bounded LangGraph nodes: proposal, interrupt for
human review, and execution. PostgreSQL checkpoints survive interpreter restart.
The resume payload cannot approve anything: the graph rechecks the domain record.
The recursion limit is eight; provider token/cost/time budgets remain pending.

`python -m workbench.mcp_server` exposes exactly five tools over stdio. Set
`MCP_PRINCIPAL_ID` in the trusted launcher. There is no identity/organization tool
argument and no approval tool. A model cannot turn a proposal into an approval.
This local transport assumes a trusted operator controls the environment; it is
not a remote multi-user OAuth service. MCP order/payment evidence is synthetic.

Tests exercise a real MCP client/subprocess, denied tools, invalid arguments,
cross-tenant requests and missing approvals. LangGraph tests restart the process
at human review, deny an unapproved resume, then resume after a domain decision.
The graph currently invokes domain functions directly; MCP transport is verified
independently and is not falsely presented as the graph's tool transport.
