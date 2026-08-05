---
id: STAGE-008
title: Fail-closed Hermes context consumer readiness
type: stage
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_plans:
  - PLAN-009
related_adrs:
  - ADR-0004
  - ADR-0005
related_evidence:
  - EVID-010
---

# STAGE-008 — Fail-closed Hermes Context Consumer Readiness

## Objective

建立Bastet-owned Hermes delivery queue到Hermes `pre_llm_call` context injection的repository-ready consumer，使用`pending → prepared → sending → delivered/ambiguous`狀態機，確保routing缺失、owner/turn不符、timeout或crash時fail closed。本Stage不安裝plugin、不啟用production dispatcher、不claim production queue、不修改或重啟`hermes-bastet.service`。

## Discovery Read-back

- Hermes正式`pre_llm_call` contract支援回傳`{"context": ...}`，context只注入目前user message的API copy，不改system prompt。
- Production Hermes已傳`turn_id`、`platform`與`sender_id`；精確conversation routing尚未傳入hook。
- Gateway-created agent已保存`_chat_id`與`_thread_id`，因此最小compatibility patch只需從`agent/turn_context.py`傳出`conversation_id`與`thread_id`，不需偽造incoming message或修改private session DB。
- `hermes-bastet.service` owner為`bastet`；目前只配置source reconciliation DB，沒有delivery DB、consumer或dispatcher ownership設定。

## Scope

- 對STAGE-007 `hermes_context_inbox`做additive schema migration。
- 提供exact platform/conversation/thread claim與owner/turn lease fencing。
- `prepared` lease過期可回到`pending`；`sending` lease過期只能進`ambiguous`，不得自動重送。
- 提供Hermes-compatible `pre_llm_call` callback；缺`platform`、`conversation_id`或`turn_id`時零claim。
- 明確拒絕空字串thread routing；`None`才代表非threaded conversation。
- 將payload包成escaped、明確標示為untrusted background data的ephemeral context。
- 建立production approval與rollback pack，但不執行其中mutation步驟。

## Explicit Non-Goals

- 不修改production Hermes checkout、plugin設定、systemd unit/drop-in或venv。
- 不套用compatibility patch，不restart service。
- 不在production執行dispatcher enable flag或建立delivery DB。
- 不claim、ack、fail、requeue或consume任何production item。
- 不呼叫Telegram或其他platform API；consumer不產生unsolicited outbound message。
- 不批准或執行remediation proposal。
- 不宣告NFS/多主機SQLite HA支援。

## Safety Invariants

1. Queue target必須exact match `platform + conversation_id + thread_id`。
2. 缺conversation routing或空thread routing時callback回傳`None`且attempts保持不變。
3. Claim與transition使用`BEGIN IMMEDIATE`及owner/turn雙重fence。
4. `prepared`表示尚未跨越handoff boundary，可在lease過期後安全重試。
5. 一旦進入`sending`，timeout/crash只可轉`ambiguous`；任何自動retry均禁止。
6. Legacy `consumed_at IS NOT NULL` row migration後必須為`delivered`且不可再claim。
7. Hook log與回傳context不得包含conversation/thread routing identifier；exception只寫固定redacted訊息。
8. Payload是資料而非指令，必須escape fence-closing markup並附untrusted instruction。
9. Repository acceptance不構成production approval。

## Acceptance Criteria

- RED→GREEN tests涵蓋routing、threadless隔離、lease recovery、ambiguous quarantine、owner/turn fencing、legacy migration與untrusted escaping。
- STAGE-007 dispatcher focused tests保持GREEN。
- Ruff format/lint、compileall、documentation governance與full repository tests通過。
- Independent review無open High/Medium finding。
- Production source/service ownership只讀read-back與approval/rollback pack完成。
- Commit、push及remote SHA read-back一致。

## Production Approval Gate

Production enablement必須另立明確批准，至少固定：Bastet release SHA、Hermes source SHA與compatibility patch digest、plugin registration artifact、delivery DB path/owner/mode、dispatcher/consumer service ownership、maintenance window、backup operator、rollback operator、existing pending與ambiguous item disposition、single-item canary target及成功/停止條件。任何欄位未決即停止。

## Next Gate

依[RUNBOOK-002](../runbooks/RUNBOOK-002-hermes-context-consumer-production-approval.md)建立獨立production enablement stage。未批准前dispatcher、consumer與compatibility patch保持disabled/unapplied。
