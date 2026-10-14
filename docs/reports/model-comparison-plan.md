# Three-arm comparison protocol — ready to run, not executed

## Current result and missing authority

The deterministic baseline and scripted reviewed workflow have reproducible local
results. The live-model arm and subjective human scores are **not run**. Unit tests
using MockTransport establish adapter behavior only, never model quality.
The adapter remains disconnected from the default graph/UI and has no approval or
execution tools. This protocol does not authorize a provider request.

Before a live run, record: explicit provider/model identifier, model revision if
available, approved total spend cap, conservative input/output price assumption,
provider-side spending limit, credential delivery outside Git, named reviewer and
the exact source commit/dataset SHA-256. A proposed USD 5 cap is a stop limit for a
small pilot, **not a price estimate or assurance that all cases fit**. If the pilot
cannot fit, stop and report the measured usage; do not raise the cap automatically.

## Freeze and reproduce

1. Use `datasets/operational-v1.json` unchanged: 42 development and 18 final cases.
   The split is public and not blinded; do not claim independent generalization.
2. On a clean checkout, run `python -m workbench.evaluate` against the disposable
   `workbench_test` database. Save stdout, source commit, dataset hash and runtime.
3. Run all objective safety/contract tests before any live-model experiment.
4. Freeze prompt/tool schemas, sampling settings and provider identifier before
   the final split. Tune only on development. No cherry-picked reruns; record every
   request, failure, refusal and timeout. Do not retry uncertain billed calls.
5. Conduct a small development pilot first. The existing `model_proposal` library
   must receive an explicit shared `RunBudget`, approved credentials/model/price
   and an authorized synthetic reader. A new budget per case must not silently
   reset the total authorized run cap. Interrupted paid runs require usage review
   before restart; durable model-spend accounting is not implemented.

## Arms and fair comparison

| Arm                        | Input and behavior                                                                                                                | What it measures                                                                       |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| A: deterministic baseline  | Current `propose(Evidence)` on every frozen case; no model and no external effect                                                 | Exact action/abstention accuracy, local latency                                        |
| B: model with read tools   | Same synthetic evidence; only get_case/get_order/get_payment_status for the server-selected case; strict unapproved Action output | Proposal accuracy, abstention, grounding, tool calls, provider tokens/cost and latency |
| C: reviewed model proposal | Reuse the exact B proposal; a real reviewer edits, approves/rejects or abstains through domain controls; sandbox-only execution   | Corrections, approval quality, reviewer time and verified effect gates                 |

Arm C must not be relabeled as a model workflow when it actually uses the current
deterministic scripted reviewer. Publish that existing regression separately.
Use the same B output for C rather than paying for an independent sample. A model
refusal/invalid output remains a failed or abstained proposal, never a fabricated
valid action. No model judges its own subjective quality.

## Retained evidence and reporting

For each case retain: dataset ID/split, source hash, raw sanitized provider output,
structured action, tool-call sequence, prompt/schema version, start/end timestamps,
HTTP outcome, provider-reported token usage and billed cost when available. Mark
reservations/estimates separately from provider-reported usage. No secrets or
private retrieved text belong in the report.

Report development/final separately: exact action accuracy, abstention precision
and recall with denominators, invalid-output/error counts, p50/p95 latency, token
totals, measured/estimated costs and every effect-gate violation. Small samples
do not establish production reliability. Compare within-case B versus C; do not
use scripted decisions as human-review results or infer people-management skill.

The [human scoring template](human-review-template.json) has 18 blank final-case
rows. Grounding/usefulness use the existing 0–2 rubric in [evaluation](evaluation.md).
Record actual reviewer identity, timestamp, observed B output, edits, decision,
scores and rationale. Null fields mean **not reviewed**, not zero quality. Publish
an aggregate only after those rows are filled by a real reviewer. Keep reviewer
identities private unless that person authorizes publication.

Acceptance: all three arms link to immutable raw evidence; no unresolved critical
effect-gate violation; costs stay within authorization; human scores have actual
provenance. If authority, budget or human input is absent, publish `not_run` /
`pending` and the concrete missing input rather than an invented comparison.
