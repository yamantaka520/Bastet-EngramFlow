---
id: EVID-012
title: Hermes context consumer controlled production rollout attempt evidence
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

# EVID-012 — Hermes Context Consumer Controlled Production Rollout Attempt

## Scope and authorization

- Repository: `/mnt/nas/Hermes-Gitlab/Bastet-EngramFlow`
- Branch/release commit: `feat/hermes-production-reconciliation-hook` / `72c5c7af4d1143fcf005d78902ce822abe557085`
- Maintenance window: 2026-08-06 09:27–10:00 CST（UTC+8）
- Explicit approval: exact pinned patch/wheel/plugin, private delivery DB, service stop/restart, one pre-existing opaque canary item with `max-items=1`, read-back, and necessary rollback.
- Approval record: owner-private backup artifact `stage9-approval-20260806_092700.txt`; SHA-256 `a12467d9df5d6d666649bdd3e68e5775f8582b52e5a6e8eb1b47f23b4fdc8026`.
- Secrets and exact routing identifiers are not retained in this repository.

## Artifact and preflight gates

- Hermes base commit: `d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`.
- Compatibility patch SHA-256: `1741f6c7d77d0cb13c1dfcb74cb8acc18a5db054a2999fb6c588bc075c4f1eda`.
- Wheel SHA-256: `3791465422639feb80e8a6fd459cb575839029bcf1cad28a871e105379c018d7`.
- Plugin manifest/init SHA-256: `08e26d49ff8343ae1ca31736dcb096fb6262f1dba1729bf17e78d6b1d17199e2` / `825d5179d8150a9e3049028f3e1cbc8088b1810e282d2faaa8169fac88ff2b67`.
- Manifest read-back and all four actual artifact hashes matched.
- Source verifier before deployment: `applicable`; after patch: `applied`.
- Source outbox before dispatch: exactly one `pending` row, attempts 0, no lease or delivery; opaque item hash prefix `bc259dc8e1d9fe53`.
- Canonical source-pinned compatibility runner: `3 passed in 0.35s`.
- Fresh delivery DB: owner `bastet`, mode `0600`, integrity `ok`, both tables empty.
- Plugin allowlist: enabled as user plugin without built-in tool override.

## Deployment and transport health

- Dedicated venv, fixed wheel, plugin, drop-in, delivery DB and compatibility patch were installed only after the stop gate returned `MainPID=0`.
- `hermes-bastet.service` started active/running.
- Authoritative transport gate passed from a post-start `gateway.log` line: `Connected to Telegram (polling mode)` at 2026-08-06 09:31:23 CST.
- No dispatcher was kept running; the approved CLI was invoked once with `max-items=1`.

## Single-item dispatch read-back

- CLI result: `dispatched=1`, `event=1`, `proposal=0`.
- Source row transitioned to `delivered`, attempts exactly 1, lease cleared.
- Delivery queue gained exactly one `pending` row, attempts 0; proposal count remained 0.
- Source receipt matched the sink contract `hermes-context:{delivery.event_id}:{payload_digest_prefix}`. Source outbox `item_id` and delivery `event_id` are intentionally different identities; equality between those columns is not a valid invariant.
- Both SQLite integrity checks returned `ok`.
- Gateway log search found zero occurrences of the opaque source hash, sink-receipt prefix, payload column marker, conversation marker, or thread marker.

## Canary failure and stop condition

- The approved real incoming Telegram turn reached the Bastet gateway at 2026-08-06 09:34:40 CST.
- Agent initialization failed before `pre_llm_call`; delivery remained fail-closed at `pending`, attempts 0, with no `prepared`, `sending`, `delivered`, or `ambiguous` timestamp.
- Root cause was outside the context consumer: `AgyCliError: agy executable failed trust/version validation`.
- Configured `AGY_CLI_SHA256`: `edec0312023c2e062e2080c8989ff86a74342c0fde6bd7e3e4cfb6528e795753`.
- Actual `/home/bastet/.local/bin/agy` SHA-256: `4217db798fd514cedce4e315013daea471a1a67666ab91547b2ad0dbee167a71`.
- Updating or bypassing the trust pin was outside the approval scope, so no provider/config mutation was attempted and the canary was not retried.

## Rollback and final production state

- Service writers were stopped and `MainPID=0` was verified before evidence capture.
- SQLite online backups were written under owner-private `rollback2-20260806_093935/`:
  - `hermes-delivery.pending.sqlite3`: integrity `ok`, one context row and zero proposals; SHA-256 `95855b3717005388875041ce824c7d63b3cd8b79cdbb64fb6e2735465ffe62ca`.
  - `reconciliation-post-canary.sqlite3`: integrity `ok`, one outbox row and two run rows; SHA-256 `384c27b1e98d5187197d0b0177ba540d7a67c20e9ee86e1c81ea271e3410b036`.
- Plugin was disabled; compatibility patch was reversed; plugin directory, dedicated venv, systemd drop-in and live delivery DB were removed. The live delivery DB was quarantined rather than deleted.
- Reverse read-back confirmed the patch is again `applicable`; plugin listing has no `bastet-context-consumer` row.
- Baseline gateway restarted active/running and reconnected to Telegram at 2026-08-06 09:41:13 CST.
- Source outbox remains `delivered`, attempts 1. The quarantined delivery row remains `pending`, attempts 0, with no ambiguous state. It must not be replayed or reset without a new per-item decision.
- AGY trust gate remains failed; transport connectivity therefore must not be represented as end-to-end agent health.

## Subsequent prerequisite remediation

- The statements above describe the final state of this rollout attempt at 09:41 CST.
- EVID-013 records a later, separately approved AGY-only remediation. It proved the live executable byte-identical to the official checksum-verified 1.1.10 release, updated the stale trust pin and passed a representative Hermes primary-route functional gate.
- That follow-up closes the external AGY prerequisite but does not replay this canary or change this rollout's rolled-back context-consumer state.

## Verdict

- Artifact deployment mechanics and one-item dispatch/read-back: PASS.
- End-to-end exact-target consumer canary: NOT COMPLETED.
- Necessary rollback: PASS.
- Production context consumer enablement: WITHHELD.
- Historical blocker at attempt closure: independently validate the replacement AGY executable and approve a new trust pin or restore the previously pinned binary. This prerequisite was subsequently closed by EVID-013; a new canary still requires fresh authorization and per-item disposition.
