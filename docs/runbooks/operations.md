# Local operation and recovery

Use `docker compose up --build -d` with POSTGRES_PASSWORD set to a local value.
Then run `docker compose exec api python -m workbench.identity` once to create
synthetic identities. PostgreSQL and API have no published ports; Next binds only
to 127.0.0.1:3200. The web image bakes its API origin at build time. IMAGE_TAG should
be a Git commit in any reproducible release; the default local tag is development-only.

The optional worker runs with `docker compose exec api python -m workbench.worker`.
It polls approved/uncertain domain cases, uses the recorded reviewer identity and
revalidates current authorization. Use one worker for this demonstration. The UI
also supports explicit execution. No distributed scheduling or lifetime retry
budget is claimed. Unknown calls remain in PostgreSQL after crashes; resume looks
up the sandbox result before retrying an effect.

## Backup, restore and rollback

Quiesce API/worker writes for a consistent operational checkpoint. Create a custom
dump with `docker compose exec -T postgres pg_dump -U workbench -Fc workbench > backup.dump`.
Store it encrypted outside the host; no offsite backup service is configured here.
Restore into a new database, never over the active one. Use PostgreSQL 18 client
tools, `createdb`, then `pg_restore --exit-on-error -d <new-database> backup.dump`.
The CI reproduces this against workbench_restore_test and compares every public
and sandbox table by row count and SHA-256, including nonempty effects/checkpoints.
Review the uploaded restore report and run a controlled resume before switching traffic.

Migrations are additive in this iteration. For application rollback, select the
previous immutable image tag and preserve the newer database schema. Do not remove
approval/journal data or restore an old snapshot over a provider's newer effects.
This is a documented procedure; an actual production rollback has not been run.

`docker compose down` removes containers/network and preserves the named database
volume. Deleting the volume is destructive and is not part of routine teardown.
No AWS resources are created by this project. The portfolio's proportional AWS
proposal is documented in Commerce; it has only static validation.

## Observability and limitations

FastAPI emits request ID, path, status and duration. Worker events include case ID
and error type without credentials or retrieved text. Domain audit rows record
decisions/edits/cancellation/effect verification. There is no external telemetry
collector or hosted alerting. Graph budgets apply per invocation, not across all
resumes; SQL timeouts bound queries, but the elapsed-time gate is cooperative.
The sandbox uses an independent transaction on the same PostgreSQL server, not an
external provider. Human review quality and LLM comparison remain unverified.
