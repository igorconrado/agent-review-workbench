# Agent Review Workbench

A synthetic operational-exception review system under active implementation.
It is an independent portfolio project, not a reconstruction of an employer's system.

## Two-minute review

Watch the [recorded browser flow](docs/demo/review-flow.webm), inspect the
[60-case raw evaluation](docs/reports/evaluation-native-goal-2026-10-14.json), then read the
[architecture and failure sequence](docs/architecture.md). The main proof is a
process dying after a sandbox effect and recovering without duplicating it.
The [portfolio-wide evidence matrix](https://github.com/igorconrado/commerce-operations/blob/main/docs/evidence.md)
keeps verified capabilities separate from gaps.

## Current evidence

Implemented: strict structured evidence, deterministic proposal or abstention,
action/context digests, PostgreSQL review decisions with row locks, tenant and
current-role authorization, context invalidation and cancellation. A durable
execution journal reconciles sandbox effects by stable action hash after process
death. The sandbox commits in an independent transaction/schema on the same
PostgreSQL server: it models provider semantics, not network or host isolation.

Implemented browser flow: login, create synthetic case, inspect evidence, propose,
approve/reject, execute and verify, cancel, and abstain when evidence is insufficient.
FastAPI sessions use opaque hashed tokens and current database identity, same-origin
writes and HttpOnly/SameSite cookies. Set COOKIE_SECURE=true behind HTTPS.

Also implemented: reviewer edits with new approval hashes, 60-case versioned corpus,
per-invocation budgets, Docker/Compose, recovery worker and backup/restore checks.
Not yet verified: real model comparison, subjective human review or deployment.
External HTTP sandbox transport and durable lifetime budgets remain planned.
Installed dependencies do not constitute evidence of those capabilities.

Native goal hardening (2026-10-14): new effects revalidate the original approver
even when another reviewer executes. Cancelled unknown attempts now have an
authorized reconciliation-only API/UI path, including verified absence without a
new effect. Worker retries have a durable five-attempt allowance, progressive
delay and audited replay; a failing batch cannot starve later due work. Domain
approvals recover without requiring a graph checkpoint. See [operations](docs/runbooks/operations.md).

The updated local suite passed **60 Python tests** against real PostgreSQL,
including edited/context-replaced and concurrent graph resumes. The fresh
deterministic evaluation at clean commit `488e82a` passed 42/42 development and
18/18 final action/effect gates. These remain scripted-review results. The
[three-arm comparison protocol](docs/reports/model-comparison-plan.md) and
[blank human scoring template](docs/reports/human-review-template.json) prepare
the remaining authorized-model and real-reviewer work; no live result is invented.

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
browser/API flow also has integration and Chromium desktop/mobile tests.

## Run the interface

After migration (`python -m workbench.store`), seed the synthetic identities with
`python -m workbench.identity`. This development command resets fixture passwords
and roles; never use it against a real deployment. Run the API using
`python -m uvicorn workbench.api:app --host 127.0.0.1 --port 8100`, then `npm run build`
and `npx next start --hostname 127.0.0.1 --port 3200` in another terminal.
Open http://127.0.0.1:3200. Login as `ana`, `viewer`, or `cedro` with the synthetic
password `Synthetic-Test-Password`. `ana` and `cedro` belong to different tenants.
`npx playwright test` runs the browser checks against a running API and starts Next.

The API runs bounded graph calls in its worker threadpool; an optional single
worker is available via `python -m workbench.worker`. Pagination beyond the latest
50 cases and distributed abuse protection remain planned. Login has a durable per-identity budget, not an IP/global
limit. No public service is exposed.

## Verified failure boundary

The integration suite starts a child Python process, commits the independent
sandbox effect, then exits with code 86 before committing the local result.
The next invocation finds the effect by its durable key and settles the journal.
One provider effect remains. Unavailable lookup leaves the journal unknown and
does not trigger a blind retry. Cancellation blocks new effects, reports known
effects, and preserves unresolved uncertainty. Authorization is reloaded at execution.

Initial validation on 2026-10-14: 39 Python tests and four browser tests passed, including real PostgreSQL and the
process-death scenario. The initial decision slice also passed clean Linux CI:
[run 38646754031](https://github.com/igorconrado/agent-review-workbench/actions/runs/38646754031).
This bounded test gate is not a universal claim of agent safety.

## Checkpoints and restricted tools

`workbench/graph.py` runs three bounded LangGraph nodes: proposal, interrupt for
human review, and execution. PostgreSQL checkpoints survive interpreter restart.
The resume payload cannot approve anything: the graph rechecks the domain record.
The recursion limit is eight; step/call/time/token/cost gates apply per invocation.
They are not durable quotas across resumes or hard cancellation of in-flight calls.

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

## Deep review

- [Domain decisions](workbench/review.py), [effect journal](workbench/execution.py),
  [graph](workbench/graph.py), [MCP server](workbench/mcp_server.py).
- [Concurrency and permissions](tests/test_review.py),
  [process-death recovery](tests/test_execution.py), [browser tests](tests/browser/review.spec.ts).
- [Evaluation methodology and rubric](docs/reports/evaluation.md): 60/60 expected
  actions and effect gates passed. Scripted reviewers, fixed non-blinded split;
  no real-model quality or subjective human score is claimed.
- [Operations, backup, restore, rollback and teardown](docs/runbooks/operations.md).
- Individual PRs: [domain](https://github.com/igorconrado/agent-review-workbench/pull/1),
  [recovery](https://github.com/igorconrado/agent-review-workbench/pull/2),
  [graph/MCP](https://github.com/igorconrado/agent-review-workbench/pull/3),
  [interface](https://github.com/igorconrado/agent-review-workbench/pull/4),
  [evaluation](https://github.com/igorconrado/agent-review-workbench/pull/5),
  [edits/budgets](https://github.com/igorconrado/agent-review-workbench/pull/6),
  [operation](https://github.com/igorconrado/agent-review-workbench/pull/7).
  Self-authored PRs are not independent review.
