---
id: PLAN-007
title: Implement read-only reconciliation outbox shadow inspection
type: plan
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-006
related_adrs:
  - ADR-0005
related_evidence:
  - EVID-008
---

# PLAN-007 — Read-only Reconciliation Outbox Shadow Inspection

## Goal

建立一個可在local test DB與Bastet production reconciliation DB上執行的read-only shadow inspector，觀測dispatcher readiness但不取得lease、不推送conversation event、不提交remediation proposal。

## Implementation

1. 新增`SQLiteOutboxShadowInspector`及immutable report/candidate dataclasses。
2. 直接以SQLite read-only URI查詢必要metadata，避免`SQLiteReconciliationStore`初始化schema/WAL。
3. 依production claim ordering計算eligible candidate，並保留event-before-proposal causal gate。
4. 只解析event routing presence；不輸出conversation/thread ID或raw payload。
5. 新增`bastet-reconciliation-shadow` CLI與`python -m`入口。
6. Missing DB、invalid limit或schema error必須回傳exit 2且不得輸出traceback。

## Verification

- Focused unit/integration tests。
- Ruff format/lint。
- Controlled production read-only preflight。
- Full repository unittest/docs/compile gates。
- Independent review。
- Git push與remote SHA read-back。

## Production Boundary

允許：以repo source及existing Bastet bridge Python讀取production SQLite metadata。

禁止：安裝新wheel到production、修改systemd/config、建立scheduler、claim/ack/fail item、觸發Telegram或proposal sink。

## Rollback

本Plan沒有production persistent mutation，因此production rollback不適用。Repository rollback為revert PLAN-007 implementation commit；既有STAGE-005 hook與ledger不受影響。
