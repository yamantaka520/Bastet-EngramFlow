---
id: REVIEW-009
title: STAGE-007 fail-closed reconciliation dispatcher readiness closure review
type: review
status: accepted
owner: independent-review
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-007
related_plans:
  - PLAN-008
related_adrs:
  - ADR-0004
  - ADR-0005
related_evidence:
  - EVID-009
---

# REVIEW-009 — STAGE-007 Closure Review

## Scope

兩輪fresh-context、read-only review檢查durable delivery queue、dispatcher CLI、tests、public packaging與治理文件。Reviewer交叉比對既有source outbox claim/ack與event-before-proposal語義；未修改repository或production。

## Round 1

Decision：conditional reject。

- High：0
- Medium：2
- Low：0

Findings：

1. Resolved-path equality無法拒絕同一SQLite檔案的hardlink alias，可能讓source與delivery schema落到同inode。
2. CLI catch-all回顯`str(exc)`，與不輸出payload/conversation identifier的claim不一致。

## Disposition

兩項均以TDD關閉：

- 新增hardlink alias regression；修復前實際重現SQLite `disk I/O error`，修復後以regular-file及`Path.samefile()`檢查在mutation前exit 2。
- 新增sink exception redaction regression；修復前stderr含測試identifier/summary，修復後改為固定generic訊息且不回顯exception文字。
- Focused suite最終10 tests PASS。

## Final Review

Decision：**ACCEPT — repository readiness only**。

- Open High：0
- Open Medium：0
- Open Low：0

Verified：

- `BEGIN IMMEDIATE`內執行payload-aware idempotency；digest一致回stable receipt，不一致fail closed。
- Sink commit/source ack crash window重播不插入第二筆queue row。
- Missing enable flag/source DB、same path、same inode及path identity uncertainty均fail closed。
- CLI預設單次1項、最大100項；成功只輸出aggregate counts，失敗不輸出exception message。
- Event-before-proposal ordering沿用權威`SQLiteReconciliationStore.claim()`語義。
- Queue實作stable Hermes context/proposal seam，不import Hermes private module、不呼叫platform adapter。
- Full repository gate：40 files formatted、Ruff lint PASS、81 tests PASS、docs governance PASS、compileall PASS、diff check PASS。
- 文件明確區分repository readiness與production enablement。

## Production Approval Pack

Decision：**NOT APPROVED / WITHHELD**。

本Review不批准以下操作：

- 在production執行`bastet-reconciliation-dispatch --enable-dispatch`。
- 建立production delivery DB或claim/ack/fail/requeue既有outbox item。
- 建立systemd unit/timer/cron或修改、重啟`hermes-bastet.service`。
- 啟用Hermes queue consumer、Telegram或其他platform delivery。
- 批准或執行remediation proposal。

未來production approval至少必須提供：

1. Hermes gateway queue consumer stable seam與consumption ledger/idempotency測試。
2. External delivery timeout/crash的ambiguous狀態與no-auto-retry規則。
3. Dispatcher/consumer service ownership、least privilege、health/read-back與bounded batch設定。
4. Source/queue backup、stop-first rollback、schema compatibility與restore rehearsal。
5. 現有pending item的一次性處置、target read-back與operator approval。
6. Production preflight、canary、stop condition及post-enable evidence。

## Acceptance

STAGE-007可在final docs/diff gate、commit、push及remote SHA read-back通過後完成repository publication closure。Production rollout仍被明確阻擋，必須另立Stage/Plan並取得使用者明示批准。
