---
id: PLAN-008
title: Implement fail-closed reconciliation dispatcher readiness
type: plan
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-007
related_adrs:
  - ADR-0004
  - ADR-0005
related_evidence:
  - EVID-009
---

# PLAN-008 — Fail-closed Reconciliation Dispatcher Readiness

## Goal

在不觸碰production outbox與Hermes service的前提下，完成可測試的source-outbox→durable Hermes delivery queue handoff與bounded CLI，先消除sink-success/source-ack crash window的重複queue insertion風險。

## Implementation

1. 新增`SQLiteHermesDeliveryQueue`，同時實作`enqueue_context()`與`enqueue_proposal()` stable seam。
2. Queue schema以event/proposal ID為primary key，保存canonical payload digest、payload、stable receipt、created/consumed timestamp。
3. `BEGIN IMMEDIATE`內檢查既有identity：digest一致回舊receipt；不一致fail closed。
4. 新增`bastet-reconciliation-dispatch` CLI，預設max items 1，最大100。
5. Mutation前驗證enable flag、source存在、owner、lease、limit、不同resolved path及不同inode。
6. CLI只輸出aggregate kind counts；失敗不回顯exception文字或payload-derived identifier。
7. 使用既有`DurableReconciliationService`保留event-before-proposal ordering及source lease/ack語義。

## Verification

- Focused RED→GREEN unittest。
- Ruff format/lint與compileall。
- Local temporary SQLite E2E；只對temp DB執行dispatch mutation。
- Full repository unittest/docs/diff gate。
- Fresh-context independent review與review-fix regression。
- Git commit、push及remote SHA read-back。

## Production Boundary

允許：repository code/docs、temporary local DB tests、read-only production source compatibility inspection。

禁止：在production執行enable flag、建立delivery DB、claim/ack/fail outbox、修改production source/config/systemd、重啟service、呼叫platform API或consume queue。

## Rollback

Repository rollback為revert STAGE-007 commit。因本Plan不做production mutation，沒有production rollback動作；未來production rollout必須另立runbook，包含DB backup、dispatcher stop、consumer stop、outbox/queue state read-back及不自動重送ambiguous external delivery的規則。
