---
id: EVID-014
title: Hermes context consumer fresh-canary production rollout evidence
type: evidence
status: accepted
owner: engineering
created: 2026-08-06
updated: 2026-08-06
related_goals:
  - GOAL-001
related_stages:
  - STAGE-009
related_plans:
  - PLAN-010
related_adrs:
  - ADR-0004
  - ADR-0005
---

# EVID-014 — Hermes Context Consumer Fresh-Canary Production Rollout

## Scope and authorization

- Explicit approval: `批准 20:45–21:45 CST 完整 rollout + 全新 canary + 必要 rollback`.
- Approved window: `2026-08-06 20:45–21:45 CST` (UTC+8).
- Owner-private approval artifact: `/home/bastet/.hermes/backups/bastet-engramflow/20260806_204500-fresh-canary/approval.txt`; SHA-256 `111576a24b44d3aafd4230481ebaef0e28c1b4279365d679b6fe89157faa719f`.
- Historical disposition: the previous source `delivered/attempts=1` row and matching quarantined sink `pending/attempts=0` row remain immutable evidence. They were not replayed, reset, merged or deleted.
- Approved mutation was restricted to one newly generated no-findings event, one dispatcher invocation with `max-items=1`, one exact-target incoming turn and necessary rollback.
- This approval is exhausted and creates no standing permission for another deploy, event, dispatch, replay or service mutation.

## Read-only preflight

- Production Hermes HEAD: `d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`; branch `feat/agy-cli-oauth-stdin-hardening`.
- Existing dirty paths matched the governed post-cron prerequisite allowlist exactly: `cron/scheduler.py`, `hermes_cli/plugins.py`, `tests/cron/test_post_cron_hook.py`.
- Context compatibility verifier: `state=applicable`; patch SHA-256 `1741f6c7d77d0cb13c1dfcb74cb8acc18a5db054a2999fb6c588bc075c4f1eda`.
- Release wheel SHA-256 matched manifest: `3791465422639feb80e8a6fd459cb575839029bcf1cad28a871e105379c018d7`.
- AGY executable hash and effective trust pin both matched `4217db798fd514cedce4e315013daea471a1a67666ab91547b2ad0dbee167a71`.
- Source preflight had exactly one historical `delivered/attempts=1` event and zero pending rows. Historical quarantine had exactly one `pending/attempts=0` row. Integrity checks were `ok`.
- Offline fresh-canary rehearsal used the formal `HermesPostCronBridge` and dispatcher: first enqueue `duplicate=false`, duplicate retry `duplicate=true`, dispatcher `event=1/proposal=0`, source `delivered/1`, sink `pending/0`, receipt mapping and both integrity checks PASS.

## Stop, backup and restore gate

- Backup root: `/home/bastet/.hermes/backups/bastet-engramflow/20260806_204500-fresh-canary`, owner-private mode `0700`.
- `hermes-bastet.service` was stopped and `MainPID=0` was verified before mutation.
- SQLite online backups were created for the source DB and historical quarantine; both opened successfully with `integrity_check=ok` and exact expected row states.
- Baseline config, systemd unit/drop-ins, manifest-owned Hermes files, exact patch/plugin/wheel and approval record were preserved with SHA-256 values in `backup-manifest.json`.
- Pre-rollout source snapshot SHA-256: `384c27b1e98d5187197d0b0177ba540d7a67c20e9ee86e1c81ea271e3410b036`.
- Historical quarantine snapshot SHA-256: `95855b3717005388875041ce824c7d63b3cd8b79cdbb64fb6e2735465ffe62ca`.

## Deployment gates

- Applied only the manifest-pinned exact-routing patch to `agent/turn_context.py`; post-apply verifier returned `state=applied` with production drift allowlist PASS.
- Installed the exact wheel into dedicated `/home/bastet/.hermes/venvs/bastet-engramflow`; the Hermes runtime venv dependency set was not modified.
- Installed reviewed user plugin `bastet-context-consumer` version `0.1.0`, enabled it without tool override and configured fixed owner/lease/max-events settings.
- Created fresh private delivery DB `/home/bastet/.hermes/state/bastet-engramflow/hermes-delivery.sqlite3`, owner `bastet`, mode `0600`, local filesystem, integrity `ok`, contexts `0`, proposals `0`.
- Source-pinned canonical suite: `3 passed in 0.46s`.
- A supplemental smoke first named a nonexistent class `HermesContextConsumer`; this was a harness naming error, not a runtime failure. The corrected `HermesPreLLMContextConsumer` import/constructor and nonmatching-route no-claim smoke passed, with delivery counts still `0/0`.

## Production health before canary

- Authoritative transport line after this deployment: `Connected to Telegram (polling mode)` at `2026-08-06 20:49:06 CST`.
- AGY adapter identity: `ok=true`, `hash_pinned=true`, `hash_ok=true`, `version=1.1.10`, `version_supported=true`, `stdin_transport=true`, trusted owner and safe mode.
- The first identity harness used a stale module path and failed before AGY execution. The corrected formal module `agent.agy_cli_adapter` passed; this did not mutate queues.
- Representative pre-canary Hermes main-route probe used `gemini-3.6-flash-high` and the terminal tool schema, exited `0`, returned `STAGE9_PRECANARY_FUNCTIONAL_OK` and left delivery counts `0/0`.
- Probe evidence SHA-256: `2d5f419d2b7d22219bed1a4fde9d78bccc8d5eecc502d83f0376788b3fe9b242`.

## Fresh event and single dispatch

- A new wire payload was generated through the formal `post_cron_job` schema with `success=true`, no findings, summary `STAGE-009 dedicated canary context. No action requested.` and the exact approved historical Telegram DM target read from owner-private evidence.
- Exact routing identifiers were not copied into public documentation. Their canonical route digest prefix was `834d62eb105aac6f`.
- Initial bridge invocation was blocked before execution by caller-side permission on the `0600` wire file. The corrected `bastet` Python subprocess kept the file private and returned `duplicate=false`, one outbox item.
- Pre-dispatch source state was exactly one historical `delivered/1` plus one new `pending/0`; the historical row remained field-equivalent to the pre-rollout snapshot.
- Dispatcher was invoked once with `--max-items 1 --enable-dispatch`; result: `dispatched=1`, `event=1`, `proposal=0`.
- Read-back: new source `delivered/attempts=1`, leases null, stable `hermes-context:{event_id}:{digest-prefix}` receipt; new sink `pending/attempts=0`; delivery proposals `0`; historical source unchanged.

## Real incoming-turn canary

- User confirmed the approved marker was sent to the exact Bastet Telegram DM.
- Gateway inbound timestamp: `2026-08-06 20:54:01 CST`.
- Fresh context durable delivery timestamp: `2026-08-06 20:54:03.795733 CST`.
- Gateway response ready timestamp: `2026-08-06 20:54:12 CST`, elapsed `11.0s`, `api_calls=1`; response was sent by the normal Telegram adapter.
- Fresh sink final state: `delivered/attempts=1`, prepared/sending/delivered timestamps present, lease fields cleared, no ambiguous timestamp.
- Fresh source final state: `delivered/attempts=1`; source receipt maps to the fresh sink event ID.
- Final source aggregate: two `delivered/attempts=1` events (one historical, one fresh). Final live delivery aggregate: one `delivered/attempts=1` fresh context, zero proposals.
- Historical source remained field-equivalent to the pre-rollout snapshot. Historical quarantine remained `pending/attempts=0` with all delivery lifecycle timestamps null.
- Source, live delivery and historical quarantine integrity checks all returned `ok`.

## Post-canary evidence and live state

- Post-canary source snapshot SHA-256: `07562e950959376c9928f859d020bf8af3740ab8bf31cbefe79c2bcc0df471c4`.
- Post-canary delivery snapshot SHA-256: `991dc37d50af2720b3b15bca0ecf43acf0730ff069eb3231318f86fc373ca7f1`.
- Fresh wire SHA-256: `60012f592ce76bcb7c7cd950e01944fe00f04ee4ee2181019904b79a253c70b9`.
- Enqueue receipt SHA-256: `287f3e2057a81eaaa6456e222e8a82d8bd59799ef1a5b42dc3b2c8236e182860`.
- Dispatch receipt SHA-256: `6ae5e3961acca3a8b7a826ab365e94bb688946e347ec7e901046ae63ec9324ea`.
- `hermes-bastet.service`: active/running after canary.
- Exact-routing patch, dedicated venv, plugin, consumer drop-in and live delivery DB remain deployed. Dispatcher is not a resident process and was invoked only once.

## Verdict

- Fresh dedicated canary event creation: PASS.
- Single-item source-to-sink dispatch: PASS.
- Exact-target pre-LLM consumption and normal AGY response: PASS.
- Historical pair no-mutation disposition: PASS.
- Rollback: not required.
- STAGE-009 production context-consumer enablement: ACCEPT, subject to independent closure review and repository governance gates.
