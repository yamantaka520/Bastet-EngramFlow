# Bastet Hermes Context Consumer Production Approval / Rollback Pack

Status: **NOT AUTHORIZED**. This document is a future-stage checklist, not permission to run mutation commands.

## Fixed current ownership (read-only discovery)

- Service: `hermes-bastet.service`
- Service owner: `bastet`
- Hermes checkout: `/home/bastet/.hermes/hermes-agent`
- Current observed Hermes HEAD: `d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`
- Existing source DB environment: `BASTET_RECONCILIATION_DB`
- Proposed delivery DB environment: `BASTET_HERMES_DELIVERY_DB` (not configured)
- Consumer seam: Hermes `pre_llm_call`
- Exact routing source: `agent._chat_id` and `agent._thread_id`
- Durable state machine: `pending → prepared → sending → delivered/ambiguous`

Any change in service owner, checkout, HEAD, source patch state or hook contract is a stop condition and requires a new compatibility review.

## Approval record required before any mutation

Record all fields; any blank field means NOT APPROVED:

1. Approved maintenance window and explicit production approver.
2. Exact Bastet-EngramFlow release commit and wheel SHA-256.
3. Exact Hermes base commit, changed-path allowlist and compatibility patch SHA-256.
4. Reviewed plugin registration artifact and its SHA-256.
5. Delivery DB absolute path, filesystem type, owner`bastet`, directory mode`0700` and DB mode`0600`.
6. Named deployment, verification and rollback operators.
7. Source reconciliation DB and delivery DB backup paths plus verified restore commands.
8. Dispatcher and consumer process ownership, single-writer assumptions and restart policy.
9. Read-only counts for source pending/leased/failed and delivery pending/prepared/sending/delivered/ambiguous.
10. Written disposition for every pre-existing pending/prepared/sending/ambiguous row. No bulk implicit adoption.
11. Approved single canary event and exact target conversation/thread.
12. Canary timeout, success conditions, stop conditions and observation period.

## Required compatibility patch (design only)

The production callsite currently passes`turn_id` but not exact conversation routing. The approved patch may only add these kwargs to the existing`pre_llm_call` invocation in`agent/turn_context.py`:

```python
conversation_id=getattr(agent, "_chat_id", None),
thread_id=getattr(agent, "_thread_id", None),
```

The patch must not infer conversation from`sender_id`, fake an incoming message, alter the system prompt, write private session DB records, or call a platform adapter. Apply and test it first in an isolated clone of the exact pinned source; compute a digest and perform independent review before production approval.

## Preflight (read-only)

- Verify service owner, ExecStart, active state and current PID.
- Verify Hermes HEAD and ensure changed paths equal the previously governed patch allowlist only.
- Verify the exact `pre_llm_call` contract and agent chat/thread attributes still exist.
- Verify release artifacts and patch/plugin digests.
- Verify delivery filesystem is local and supported; stop on NFS/remote/unknown locking semantics.
- Run full Bastet gates and source-pinned Hermes compatibility tests in isolated environments.
- Inspect queue state with a read-only connection; do not let a constructor create or migrate the production DB during preflight.

## Backup gate (mutation; separately authorized)

1. Stop the approved dispatcher/consumer writers before snapshotting.
2. Use SQLite online backup or a verified checkpoint-aware procedure; do not copy only the main file while WAL writers are active.
3. Preserve source DB, delivery DB, Hermes changed files, config/drop-ins, plugin artifact and installed release metadata in a timestamped owner-private backup.
4. Verify backup hashes and open a copy read-only to confirm schema and state counts.
5. Do not continue until restore has been rehearsed against copies.

## Deployment sequence (mutation; separately authorized)

1. Keep dispatcher disabled and stop`hermes-bastet.service` within the approved window.
2. Install the exact release into a dedicated service-owner venv without modifying the Hermes runtime venv dependencies.
3. Apply only the approved compatibility patch; changed-path read-back must match its manifest.
4. Register only the reviewed`pre_llm_call` consumer plugin; configure a private delivery DB path and fixed owner identity.
5. Run source-pinned tests and config/plugin load validation before service start.
6. Start Hermes with dispatcher still disabled; verify service health and that missing routing produces zero claims.
7. Enable only the approved one-item canary dispatch, then disable dispatcher again.
8. Trigger one real incoming turn in the approved exact target and verify the context is attached to that turn only.

## Canary success criteria

- Exactly one approved new row enters the delivery queue.
- State reaches`delivered` through`prepared` and`sending`, with attempts exactly one.
- Wrong platform/chat/thread and missing routing produce no claim.
- No unsolicited Telegram/platform message is emitted by the consumer.
- The stored user content remains clean; injected context appears only in the API-side turn context.
- Logs contain no payload, conversation/thread ID or raw exception.
- Source outbox and queue read-back reconcile to the same stable event identity.

## Immediate stop conditions

- Any unapproved changed path, dirty source drift or digest mismatch.
- Queue/database path aliasing, unsupported filesystem or ownership/mode mismatch.
- Wrong-target claim, duplicate attempt, raw identifier/payload leak or platform send.
- Any row found in`sending` after timeout or any unexpected`ambiguous` row.
- Service fails health checks or pre-existing queues change outside the approved canary.

## Rollback sequence

1. Disable/stop dispatcher first so no new production item is created or claimed.
2. Stop consumer/Hermes and verify writer PIDs are gone.
3. Record immutable read-only copies and counts of every queue state before changes.
4. Treat all`sending` rows as`ambiguous`; never reset or auto-retry them during rollback.
5. Restore the approved Hermes files/config/drop-ins/plugin and prior release from verified backups.
6. Quarantine the delivery DB; do not delete it or merge it back into source state.
7. Start the previous Hermes configuration and verify normal conversation health without consumer registration.
8. Reconcile source and delivery IDs offline. Any manual ambiguous resolution requires per-item human approval and evidence.

## Production boundary

STAGE-008 does not authorize any step under Backup, Deployment or Rollback. It does not create the delivery DB, patch Hermes, install a plugin, enable the dispatcher/consumer, restart the service, claim an item or call Telegram/platform APIs.
