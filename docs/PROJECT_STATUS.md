---
id: STATUS-001
title: Bastet-EngramFlow 專案狀態
type: status
status: active
owner: project-maintainers
created: 2026-08-05
updated: 2026-08-05
---

# Bastet-EngramFlow 專案狀態

- 最後更新：2026-08-05 09:10 CST（UTC+8）
- 已完成階段：`STAGE-000` Runtime-neutral foundation
- 已完成階段：`STAGE-001` Scheduled execution reconciliation core
- 已完成階段：`STAGE-002` Durable reconciliation delivery
- 目前狀態：STAGE-002 accepted；production Hermes hook 尚未啟動
- 工作分支：`feat/durable-reconciliation-delivery`
- Foundation commits：`ee4dc13afaf9ebf293dcfea848979b3762687cd8`、`4958b501869050b5bdbec33d299cbafc8cb87116`

## Active Goals

- [GOAL-001](goals/GOAL-001-runtime-neutral-governed-continuation.md)：建立跨 Agent Runtime 的受治理主動專案延續能力。

## Accepted STAGE-002 Deliverables

- [STAGE-002](stages/STAGE-002-durable-reconciliation-delivery.md)：SQLite ledger/outbox、lease recovery 與 structured adapter seam。
- [PLAN-003](plans/PLAN-003-durable-reconciliation-delivery.md)：durable enqueue/dispatch、Hermes result mapping、conversation/proposal adapter contracts 與 failure tests。
- ADR-0004：SQLite transactional outbox + at-least-once delivery；sink 必須 idempotent。
- [EVID-003](evidence/EVID-003-durable-reconciliation-delivery.md)：45 tests 與完整 static/docs gates，狀態 `accepted`。
- [REVIEW-003](reviews/REVIEW-003-durable-reconciliation-delivery.md)：三輪 fresh-context review，Final High 0 / Medium 0，狀態 `accepted`。
- Production 邊界：未修改 Hermes `_process_job()`、gateway session、cron service 或 Telegram production routing。

## Accepted STAGE-001 Deliverables

- [STAGE-001](stages/STAGE-001-scheduled-execution-reconciliation.md)：scheduled execution result/finding 回流與 remediation boundary。
- [PLAN-002](plans/PLAN-002-scheduled-execution-reconciliation.md)：reconciliation models、policy、ports、coordinator 與 tests。
- ADR-0003：structured reconciliation event + governed remediation proposal。
- [EVID-002](evidence/EVID-002-scheduled-execution-reconciliation.md)：30 tests 與完整 static/docs gates，狀態 `accepted`。
- [REVIEW-002](reviews/REVIEW-002-scheduled-execution-reconciliation.md)：Final read-back High 0 / Medium 0，狀態 `accepted`。

## Accepted Foundation Deliverables

- [STAGE-000](stages/STAGE-000-foundation.md)：runtime-neutral contract 與治理基線。
- [PLAN-001](plans/PLAN-001-runtime-neutral-foundation.md)：文件治理與 Agent Runtime SPI 第一個工程增量。
- [EVID-001](evidence/EVID-001-runtime-neutral-foundation.md)：19 tests、Ruff、docs checker、compileall、diff 與 audit 證據。
- [REVIEW-001](reviews/REVIEW-001-runtime-neutral-foundation.md)：三輪獨立 read-back，最終無未處理 High/Medium finding。
- ADR-0001：runtime-neutral core + thin runtime adapters。
- ADR-0002：repository-native 文件治理與穩定 ID。

## Foundation Result

- 建立 immutable runtime models、AgentRuntime Protocol、capability registry 與標準錯誤。
- Worker lifecycle 與 independent verification lifecycle 分離。
- Runtime selection 依 capabilities，不依 vendor version 字串。
- 文件治理檢查可偵測 broken ID、broken Markdown link 與無 EVID 的 Supported claim。
- Compatibility matrix 對未完成真實 E2E 的 runtime 不做虛假 Supported 聲明。

## Blockers

- 無。

## Current Risks

- SQLite reference store 為單一 filesystem/database boundary；NFS/多主機 locking 與 HA 尚未宣告支援。
- Delivery 為 at-least-once；sink 若不以 stable event/proposal ID 去重，crash window 仍可能重複投遞。
- Sink receipt 與 exception text 尚未有獨立 byte cap，列為 Low residual storage-growth risk。
- Hermes adapter 目前是 public structured seam contract，尚未接入 production scheduler/gateway hook。
- Remediation proposal 只入 queue，不代表已批准、已執行或已驗證。

## Next Gate

Production Hermes integration 必須另建 Stage/Plan，至少涵蓋：

1. 在 pinned Hermes version 的 `_process_job()` 結果/delivery receipt 後接入 capture hook。
2. Durable conversation ingress 與 remediation proposal queue 的真實 implementation。
3. Telegram 原 thread delivery、next-turn context consumption 與 independent read-back。
4. Sink receipt/error cap、retry backoff/dead-letter、queue pause/drain 與 rollback。
5. Crash/restart、duplicate delivery、prompt injection、secret/redaction 與 service rollback E2E。
