---
id: REVIEW-012
title: STAGE-009 controlled production rollout attempt closure review
type: review
status: blocked
owner: independent-review
created: 2026-08-06
updated: 2026-08-06
related_goals:
  - GOAL-001
related_stages:
  - STAGE-009
related_plans:
  - PLAN-010
related_evidence:
  - EVID-011
  - EVID-012
---

# REVIEW-012 — STAGE-009 Controlled Production Rollout Attempt Closure

## Scope

Review the approved second deployment attempt, exact one-item dispatch, real incoming-turn failure, fail-closed queue state, necessary rollback, final baseline state and remaining production blocker. This review does not approve AGY trust-pin changes, delivery replay, source reset or another canary.

## Findings

### High — transport health was insufficient as the final pre-dispatch health gate

- Observation: `gateway.log` proved Telegram polling connectivity, but the first real incoming turn failed during primary LLM client initialization before `pre_llm_call`.
- Evidence: actual AGY executable SHA-256 did not match the pinned `AGY_CLI_SHA256` service environment.
- Containment: consumer did not claim the row; delivery remained `pending/attempts=0`; no `sending` or `ambiguous` state occurred; rollout was rolled back.
- Remediation: RUNBOOK-002 now requires provider executable trust/version validation and a bounded agent-initialization functional gate before one-item dispatch.
- Status: deployment risk contained; external AGY prerequisite remains an open production blocker.

### Medium — source and sink primary keys were initially compared using an invalid equality assumption

- Observation: the first read-back assertion compared source `item_id` directly to delivery `event_id`.
- Evidence: code inspection confirmed dispatch decodes the event and enqueues `event.event_id`; the source receipt stores the sink receipt.
- Correct invariant: source receipt equals `hermes-context:{delivery.event_id}:{payload_digest_prefix}`.
- Remediation: closure evidence records the receipt mapping and does not use raw identifier equality.
- Status: closed; no state mutation resulted from the failed assertion.

### Medium — first watcher ran under the wrong filesystem identity

- Observation: a read-only watcher under `neo` could not traverse the owner-private `bastet` state directory and exited `database_unavailable`.
- Remediation: watcher was restarted as `bastet`; it observed `pending/attempts=0` and was terminated before rollback. Direct privileged read-back independently confirmed queue state.
- Status: closed; no queue mutation occurred.

## Verified gates

- Release artifact hashes and manifest: PASS.
- Source drift verifier before/after deployment: `applicable` / `applied`.
- Canonical source-pinned tests: `3 passed`.
- Delivery DB owner/mode/schema/integrity/empty gate: PASS.
- User plugin allowlist without tool override: PASS.
- Post-start Telegram transport gate: PASS.
- Exactly one dispatcher invocation with `max-items=1`: PASS.
- Source `delivered/attempts=1`, one sink `pending/attempts=0`, receipt mapping and no-log-leak read-back: PASS.
- Real incoming turn reached gateway: PASS.
- Consumer terminal `delivered/attempts=1`: FAIL — hook was not reached because AGY trust validation failed.
- Rollback evidence snapshots, reverse patch, plugin/drop-in/venv/live DB removal and baseline restart: PASS.
- Final ambiguity count: 0.

## Open finding count

- High: 1 — external production prerequisite: deployed AGY executable does not match the configured trust pin, so agent functional health is unavailable.
- Medium: 0.

## Verdict

**Rollback execution and evidence closure: ACCEPT.**

**Overall rollout closure and production context consumer enablement: WITHHELD.**

The repository artifacts remain accepted under STAGE-009, but this review stays blocked while the High prerequisite finding is open and production is back on the prior configuration. The source row is already acknowledged and its matching sink row is quarantined pending; neither may be replayed/reset automatically. A future attempt requires an independently validated AGY binary disposition, a new maintenance window, a new per-item disposition and a fresh explicit approval.
