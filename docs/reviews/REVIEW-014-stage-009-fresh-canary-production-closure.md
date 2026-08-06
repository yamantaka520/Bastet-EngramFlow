---
id: REVIEW-014
title: STAGE-009 fresh-canary production closure review
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
  - EVID-011
  - EVID-012
  - EVID-013
  - EVID-014
---

# REVIEW-014 — STAGE-009 Fresh-Canary Production Closure

## Scope

Independent read-only review of the EVID-014 fresh maintenance window, live deployment wiring, exact-routing artifact, AGY prerequisite, formal fresh-event dispatch, exact-target incoming-turn consumption, historical no-replay disposition, post-canary snapshots and governance consistency.

## Review rounds

### First round

- Confirmed `hermes-bastet.service` active/running, expected systemd consumer drop-in and consistent EVID-014 / PROJECT_STATUS / TRACEABILITY / RUNBOOK-002 narrative.
- Reported two Medium coverage gaps for private SQLite/log read-back and one Low coverage gap for live verifier execution because the first reviewer did not use the available `sudo` path.
- These were review-evidence limitations, not observed product defects, and were not treated as closed by documentation alone.

### Second round — direct privileged read-only evidence

- Used `sudo` without mutation to verify service `active/running`, expected drop-ins and live delivery DB owner/mode `bastet:bastet 0600`.
- Ran the source-pinned production verifier as `bastet`; result: Hermes base `d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`, exact-routing patch `1741f6c7d77d0cb13c1dfcb74cb8acc18a5db054a2999fb6c588bc075c4f1eda`, plugin `bastet-context-consumer`, state `applied`, production drift PASS.
- Opened source, live delivery and historical quarantine SQLite databases with URI `mode=ro`; all integrity checks returned `ok`.
- Source aggregate: two rows, both `delivered/attempts=1`.
- Live delivery aggregate: one `delivered/attempts=1`; leases clear; prepared/sending/delivered timestamps present; ambiguous timestamp null; proposal count zero.
- Historical quarantine: one `pending/attempts=0`; all lifecycle timestamps null; proposal count zero.
- Read the authoritative gateway log: one inbound event at `20:54:01 CST`, one matching response-ready event at `20:54:12 CST`, elapsed `11.0s`, `api_calls=1`. Private routing identifiers and message body were not repeated in the review output.
- Recomputed both post-canary snapshot hashes and matched EVID-014:
  - source `07562e950959376c9928f859d020bf8af3740ab8bf31cbefe79c2bcc0df471c4`
  - delivery `991dc37d50af2720b3b15bca0ecf43acf0730ff069eb3231318f86fc373ca7f1`

### Correct user-plugin path micro-review

- Corrected a non-authoritative probe that had looked under the Hermes checkout instead of the user plugin root.
- Verified `/home/bastet/.hermes/plugins/bastet-context-consumer/__init__.py` SHA-256 `825d5179d8150a9e3049028f3e1cbc8088b1810e282d2faaa8169fac88ff2b67`.
- Verified `plugin.yaml` SHA-256 `08e26d49ff8343ae1ca31736dcb096fb6262f1dba1729bf17e78d6b1d17199e2`.
- `hermes plugins list --plain --no-bundled` confirmed `enabled user 0.1.0 bastet-context-consumer`.
- Config read-back confirmed the plugin is allowlisted with `allow_tool_override: false`.

## Governance review

- EVID-012 remains an accepted closure of the first rolled-back attempt; it is not rewritten as success.
- EVID-013 remains the independently approved AGY prerequisite remediation and does not claim rollout authority.
- EVID-014 records a separate fresh approval, new event identity and preserved historical pair.
- PROJECT_STATUS and TRACEABILITY now describe STAGE-009 production enablement as accepted while preserving the historical quarantine restriction.
- RUNBOOK-002 records that the latest approval is exhausted and creates no standing authorization.
- Public documents retain only a route digest prefix; exact conversation identifiers and private wire payload remain owner-private.

## Findings

- High: 0 open.
- Medium: 0 open. The first round's two permission-related coverage gaps were closed by direct privileged read-back.
- Low: 0 open. The live verifier and correct user-plugin path/hash/enable/no-override checks were completed.

## Verdict

- Artifact identity and production drift: ACCEPT.
- AGY primary-route prerequisite: ACCEPT.
- Fresh event and bounded single dispatch: ACCEPT.
- Exact-target pre-LLM delivery and normal response: ACCEPT.
- Historical source/quarantine no-mutation disposition: ACCEPT.
- Backup and rollback readiness: ACCEPT; rollback was not required.
- STAGE-009 production context-consumer enablement: **ACCEPT / CLOSED**.
- Future mutations: **NOT AUTHORIZED** by this review or the exhausted EVID-014 window.
