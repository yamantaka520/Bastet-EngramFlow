---
id: STAGE-006
title: Reconciliation outbox shadow inspection
type: stage
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_plans:
  - PLAN-007
related_adrs:
  - ADR-0005
related_evidence:
  - EVID-008
---

# STAGE-006 — Reconciliation Outbox Shadow Inspection

## Objective

在不claim、ack、fail outbox item、不呼叫conversation/proposal sink、也不啟用production dispatcher的前提下，提供可驗證的dispatch readiness觀測。這是actual dispatcher與conversation sink deployment前的shadow-first gate。

## Scope

- 以SQLite URI `mode=ro`及`PRAGMA query_only`讀取既有durable outbox。
- 輸出bounded、non-sensitive metadata：state/kind counts、eligible count、causal blocking、expired lease、routing validity與有限candidate IDs。
- 保持event-before-proposal ordering：同run event未delivered時，proposal不得顯示為eligible。
- Missing database必須fail closed，不能建立新DB。
- 提供library API與CLI entry point。
- 對Bastet production DB只執行read-only preflight。

## Explicit Non-Goals

- 不部署或啟用production dispatcher/systemd unit/cron job。
- 不claim、renew、ack、fail或requeue任何outbox item。
- 不呼叫Telegram、Hermes conversation inbox或remediation proposal sink。
- 不輸出raw payload、summary、conversation/thread ID、receipt、last error或remediation key。
- 不授權auto-remediation或任何外部side effect。

## Safety Invariants

1. Inspector不使用會建表或改schema的store constructor。
2. Inspection前後outbox state、attempts、lease owner及lease deadline一致。
3. DB/WAL durable bytes於controlled tests中一致；SQLite reader可能更新transient `-shm` reader-lock metadata，該行為不代表outbox mutation。
4. `immutable=1`與`nolock=1`不得用於WAL-backed production inspection：前者可能看不到未checkpoint WAL，後者在實測中無法開啟DB。
5. Candidate limit必須介於1與1000，避免無界輸出。

## Acceptance Criteria

- RED test證明API缺失；GREEN tests覆蓋read-only、redaction、expired lease、causal ordering、missing DB及CLI subprocess。
- Production shadow preflight顯示routing valid，且outbox state/attempts/lease不變。
- Full repository gates全部通過。
- Fresh-context review無open High/Medium finding。
- Commit、push及remote SHA read-back一致。

## Next Gate

Actual dispatcher、conversation sink與任何outbox state mutation必須另立Stage/Plan並取得明確production approval；STAGE-006 accepted不構成該批准。
