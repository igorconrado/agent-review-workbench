# Optional model adapter — contract tested, no live model run

`workbench/model.py` implements the documented
[Chat Completions tool contract](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
It requires explicit credentials, model, conservative per-token price and budget.
No default model, secret discovery, ambient API call or paid request is performed.
It is a library adapter, not enabled in the browser or deterministic graph.

Only get_case, get_order and get_payment_status can be called, for the exact
server-selected case. A trusted caller supplies the authorized reader; it must
resolve current identity and tenant as the MCP/domain reader does. No approval or
execution tool is offered. Output is strictly validated as an Action and remains
unapproved. An operator can review it using the existing proposal-edit path.

MockTransport tests verify wire requests, read-only allowlist, immutable case
identity, strict output, zero-budget refusal and no automatic timeout retry.
These tests are **not evidence of provider compatibility, model quality or prompt
injection resistance with a real model**. The real comparison remains not run.

Budget reservations conservatively use serialized request bytes plus output/overhead
allowance; they are not billed usage or a provider-enforced spending cap. Returned
usage is retained, and exceeding the reservation stops further calls. Configure
provider-side spend limits before any live experiment. A live run needs an explicit
model, price assumption, budget, synthetic dataset and human scoring plan; credentials
must be supplied outside version control. Do not send employer or private vault data.
