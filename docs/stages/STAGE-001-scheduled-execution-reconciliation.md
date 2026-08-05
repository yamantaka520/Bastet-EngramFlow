---
id: STAGE-001
title: Scheduled execution reconciliation core
type: stage
status: accepted
owner: project-maintainers
created: 2026-08-05
updated: 2026-08-05
stage_order: 1
related_goals:
  - GOAL-001
related_plans:
  - PLAN-002
---

# STAGE-001：Scheduled execution reconciliation core

## Purpose

讓隔離執行的 scheduled agent run 將結果、問題與後續修復需求安全回流至 conversation context，並在 policy 約束下形成可追溯的 remediation proposal。

## Entry Criteria

- STAGE-000 已 accepted。
- Runtime-neutral SPI 與文件治理基線可用。
- 已確認排程 run 不應直接共享或任意改寫原 conversation session state。

## Deliverables

1. Scheduled run envelope、problem、conversation event 與 remediation proposal models。
2. Deterministic reconciliation policy 與 deduplication。
3. Conversation inbox / remediation sink ports 與 coordinator。
4. Success、failure、duplicate、approval gate、bounded auto-remediation contract tests。
5. Architecture、security、threat model、evidence 與 independent review 更新。

## Exit Criteria

- 每個有 origin conversation 的 run 可產生可投遞 context event。
- 問題可形成 remediation proposal，但 worker result 不會自動標記 resolved。
- 外部副作用、critical findings、缺少 idempotency key 或超出 continuation depth 時，不得標記為 auto-remediation eligible。
- 同一 scheduled run 在 reference coordinator instance 內不會重複完成；production 跨重啟／多實例需 durable ledger/outbox。
- Full tests、docs governance、static checks 與 independent review 通過。

## Risks

- 將「回流對話」錯作直接 session mutation，破壞訊息序列與 prompt cache。
- 問題重複回流造成 remediation storm。
- 自動重試 external side effects 導致不可逆重複操作。
- 排程輸出夾帶 secrets 或未受信任內容污染 conversation context。
