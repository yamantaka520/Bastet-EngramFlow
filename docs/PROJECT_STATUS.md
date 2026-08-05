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

- 最後更新：2026-08-05 13:29 CST（UTC+8）
- 已完成階段：`STAGE-000` Runtime-neutral foundation
- 已完成階段：`STAGE-001` Scheduled execution reconciliation core
- 已完成階段：`STAGE-002` Durable reconciliation delivery
- 已完成階段：`STAGE-003` Hermes production reconciliation hook integration
- 目前階段：`STAGE-004` production SHA reconciliation and rollout readiness
- 目前狀態：read-only production discovery完成；舊patch與production SHA不相容，isolated rebase進行中
- 工作分支：`feat/hermes-production-reconciliation-hook`
- Foundation commits：`ee4dc13afaf9ebf293dcfea848979b3762687cd8`、`4958b501869050b5bdbec33d299cbafc8cb87116`

## Active Goals

- [GOAL-001](goals/GOAL-001-runtime-neutral-governed-continuation.md)：建立跨 Agent Runtime 的受治理主動專案延續能力。

## Active STAGE-004 Deliverables

- [STAGE-004](stages/STAGE-004-hermes-production-rollout-readiness.md)：production SHA reconciliation與rollout readiness；production deployment未授權。
- [PLAN-005](plans/PLAN-005-hermes-production-rebase-readiness.md)：isolated rebase、focused E2E、artifact與rollback runbook。
- Production baseline：Hermes `d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`，clean custom branch `feat/agy-cli-oauth-stdin-hardening`。
- Discovered blocker：STAGE-003 patch對production scheduler/plugin hunks均不適用；禁止直接套用。

## Accepted STAGE-003 Deliverables

- [STAGE-003](stages/STAGE-003-hermes-production-reconciliation-hook.md)：pinned Hermes observer hook與durable bridge integration，狀態`accepted`。
- [PLAN-004](plans/PLAN-004-hermes-post-cron-hook.md)：source patch、shell bridge、restart/replay與thread-origin E2E。
- ADR-0005：fail-open `post_cron_job` unified hook + allowlisted shell bridge。
- [EVID-004](evidence/EVID-004-hermes-post-cron-hook.md)：clean apply、211項Hermes integration tests與63項Bastet full gate。
- [REVIEW-004](reviews/REVIEW-004-hermes-post-cron-hook.md)：final High 0 / Medium 0，狀態`accepted`。
- Pinned baseline：Hermes `1072c0725115e9be0491ca4cb0d965b9f5f59874`；patch SHA-256 `2fa36a110d7dcf9a3fb5846ede59c95a5162edbea6f4c792b7026079a7d30c5b`。
- Production boundary：production checkout、config與services均未修改或重啟。

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

- SQLite reference store為單一filesystem/database boundary；NFS/多主機locking與HA尚未宣告支援。
- Delivery為at-least-once；sink仍須以persisted event/proposal ID去重。
- Hermes run UUID只在單一emitted payload內穩定，不代表跨job re-execution business identity。
- Source-pinned integration已驗證，但production checkout/config/service與真實Telegram API delivery尚未部署或read-back。
- Remediation proposal只入queue，不代表已批准、已執行或已驗證。

## Next Gate

Production rollout必須另建Stage/Plan並取得明確核准，至少涵蓋：

1. Snapshot與reconcile production Hermes dirty/diverged source及config，不直接覆蓋local changes。
2. Dedicated Bastet venv、durable local SQLite path與exact shell-hook allowlist approval。
3. 套patch前preflight、service maintenance window、baseline與patched smoke tests。
4. 真實Telegram原thread delivery/read-back與next-turn context consumption。
5. Queue pause/drain、crash/restart、duplicate delivery與reverse-patch rollback演練。
