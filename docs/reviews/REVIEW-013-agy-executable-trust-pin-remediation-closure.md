---
id: REVIEW-013
title: AGY executable trust-pin remediation closure review
type: review
status: accepted
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
  - EVID-012
  - EVID-013
---

# REVIEW-013 — AGY Executable Trust-Pin Remediation Closure

## Scope

Independently review the live AGY executable/pin relationship, Bastet service state, rolled-back context-consumer artifact boundary, source/quarantine SQLite state and documentation consistency after the separately approved AGY-only remediation. This review does not authorize context-consumer deployment, row replay/reset, dispatcher execution or another canary.

## Independent live read-back

- Exact unit `hermes-bastet.service`: `active/running`; observed `MainPID=2488484`.
- Effective `AGY_CLI_SHA256`: `4217db798fd514cedce4e315013daea471a1a67666ab91547b2ad0dbee167a71`.
- Live `/home/bastet/.local/bin/agy` SHA-256: exact match to the effective pin.
- Context-consumer plugin directory, dedicated venv, consumer drop-in and live delivery DB: all absent.
- Source SQLite opened with URI `mode=ro`: exactly one reviewed row at `delivered/attempts=1`, lease owner/until null; integrity `ok`.
- Quarantine SQLite opened with URI `mode=ro`: exactly one reviewed row at `pending/attempts=0`, prepared/sending/delivered/ambiguous timestamps all null; integrity `ok`.
- No IDs, payloads, conversation/thread routing or secrets were retained in the review output.

## Documentation consistency

- EVID-012 preserves the historical failed prerequisite and rollback state, then points to the separate follow-up remediation without rewriting the failed canary as successful.
- EVID-013 supplies the official manifest/archive/executable checksum chain, isolated version probe, authorized mutation, rollback behavior, final identity/transport/main-route functional gates and queue no-mutation read-back.
- REVIEW-012 now distinguishes `rollout-attempt closure: ACCEPT (rolled back)` from `production context consumer enablement: WITHHELD`.
- PROJECT_STATUS, TRACEABILITY and RUNBOOK-002 use the same boundary: AGY prerequisite closed; consumer rollout remains rolled back and requires a fresh window, per-item disposition and explicit approval.
- The first review's Low commit-field ambiguity is closed: RUNBOOK-002 identifies the older value as artifact-lineage context and requires every future approval to pin the exact deployment commit separately.
- The first review's Low test-evidence gap is closed: EVID-013 records the focused `33 passed`, diff check and compileall evidence plus the non-gating NAS cache warning.

## Finding count

- High: 0.
- Medium: 0.
- Low: 0 open.

## Verdict

**AGY executable trust-pin remediation: ACCEPT.**

**STAGE-009 rollout-attempt closure: ACCEPT (rolled back).**

**Production context consumer enablement: WITHHELD.**

The external AGY prerequisite is closed, but no context-consumer artifact is live and no queue row has been replayed or reset. Any future production attempt remains subject to RUNBOOK-002 and requires a new maintenance window, explicit disposition for the acknowledged source row and quarantined sink row, repeated provider functional-health gates and fresh deployment/canary/rollback authorization.
