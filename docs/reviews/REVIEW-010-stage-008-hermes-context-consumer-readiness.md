---
id: REVIEW-010
title: STAGE-008 fail-closed Hermes context consumer readiness review
type: review
status: accepted
owner: independent-review
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-008
related_plans:
  - PLAN-009
related_adrs:
  - ADR-0004
  - ADR-0005
related_evidence:
  - EVID-010
---

# REVIEW-010 — STAGE-008 Hermes Context Consumer Readiness

## Scope

Review queue migration, exact routing, concurrency and lease semantics, ambiguous-delivery quarantine, untrusted context handling, Hermes compatibility assumptions, governance boundary and regression coverage. Production deployment approval is outside this review.

## Round 1

Independent review result: High 0 / Medium 1.

Medium finding: a provided empty`thread_id` was normalized to`None`, allowing it to match a threadless row. Required fix: empty provided thread routing must fail closed without claim.

Requested regressions included legacy consumed-row migration, platform/threadless isolation and untrusted fence escaping.

## Engineering Response

- Added RED regression reproducing the empty-thread claim.
- Added legacy consumed-row fixture, which exposed a second migration defect caused by additive-column default behavior.
- Changed empty thread routing to immediate no-op.
- Changed migration to map`consumed_at IS NOT NULL` to`delivered` and backfill`delivered_at`.
- Added exact platform/threadless and fence-closing payload tests.
- Combined focused gate: 20 tests PASS; Ruff lint PASS.

## Final Independent Read-back

Final result after Round 1 fixes and governance updates:

- High: 0
- Medium: 0
- Low: 2 non-blocking observations

Low observations：reviewer的isolated shell未設定repository`PYTHONPATH`，因此其focused pytest collection無法重現；工程方的canonical command已以explicit`PYTHONPATH`完成91 tests PASS。Reviewer另建議明載`NULL`代表non-threaded conversation；STAGE-008 Safety Invariant 1–2與Scope已固定`None`/empty routing語義，故無額外code change。

Round 1 empty-thread finding已由regression及read-back關閉；legacy consumed-row migration、exact routing、prepared/sending recovery、owner/turn fencing與untrusted context均符合要求。

## Verdict

- Repository readiness: **ACCEPT**
- Production approval: **WITHHELD**

Repository acceptance不批准production dispatcher/consumer enablement、Hermes compatibility patch、plugin installation/configuration、delivery DB creation/migration、queue claim或service restart。下一stage必須依RUNBOOK-002重新取得明確批准。
