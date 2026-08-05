---
id: PLAN-002
title: 排程執行回流與主動修復核心
type: plan
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-001
related_adrs:
  - ADR-0003
related_evidence:
  - EVID-002
---

# PLAN-002：排程執行回流與主動修復核心

## Objective

建立 runtime-neutral reconciliation core，讓 scheduled execution 的結果與問題成為可投遞、可追溯的 conversation context event；需要後續處理時形成 bounded remediation proposal，交由 policy gateway 與 runtime router 決定是否執行。

## Scope

### In scope

- Immutable scheduled run envelope、origin reference、finding 與 reconciliation models。
- Conversation inbox 與 remediation proposal sink ports。
- Deterministic policy：discussion、proposal、auto-remediation eligibility。
- Run ID deduplication 與 delivery/proposal receipts。
- Risk、idempotency、depth、action class gates。
- Unit/contract tests、架構與治理文件。

### Out of scope

- 修改 Hermes scheduler、gateway 或 production cron configuration。
- 直接注入 vendor session message history。
- Durable database/event bus implementation。
- 未經 policy gateway 的自動外部副作用。
- 真實 runtime adapter 與 production remediation execution。

## Work Items

1. `DOC-05`：建立 STAGE-001、PLAN-002、ADR-0003。
2. `TST-03`：先建立 reconciliation policy/coordinator 失敗測試。
3. `IMP-04`：實作 immutable envelope、finding、proposal、decision 與 receipt。
4. `IMP-05`：實作 policy evaluator、deduplication 與 coordinator ports。
5. `DOC-06`：更新 architecture、security、threat model、traceability 與 status。
6. `EVID-02`：記錄可重現驗證。
7. `REV-02`：獨立 diff review 與 remediation。

## Deliverables

- `src/bastet_engramflow/reconciliation/`
- `tests/test_scheduled_reconciliation.py`
- `docs/adr/0003-scheduled-execution-reconciliation.md`
- `docs/evidence/EVID-002-scheduled-execution-reconciliation.md`
- `docs/reviews/REVIEW-002-scheduled-execution-reconciliation.md`

## Acceptance Criteria

1. 有 origin conversation 的 successful/failed run 都可產生 conversation event。
2. Retryable finding 可產生 remediation proposal，並保留 run lineage、why_now 與 acceptance criteria。
3. Critical、external-side-effect、non-idempotent 或 depth-exhausted proposal 必須要求人工 approval。
4. Core 只判斷 auto-remediation eligibility，不直接宣稱問題已修復或 verified。
5. 同一 `(schedule_id, run_id)` 在 reference coordinator instance 內只完成一次；production system-wide 去重明列為 durable adapter 後續工作。
6. Sink failure 不得被誤報為已完成；event/proposal stable IDs 與 idempotent sink contract 支援 partial-success retry。
7. 無 origin conversation 時仍回傳 durable reconciliation decision，但不假造 session delivery。
8. Full tests、docs checker、Ruff、compileall 與 independent review 通過。

## Verification

- `python -m unittest discover -s tests -v`
- `python scripts/check_docs.py`
- `ruff format --check .`
- `ruff check .`
- `python -m compileall -q src scripts tests`
- `git diff --check`

## Risks and Mitigations

- **Remediation storm**：run key deduplication、continuation depth 與 proposal receipt。
- **Unsafe replay**：idempotency key 與 action class gate；external side effects 一律 approval-gated。
- **Session corruption**：只透過 inbox event port 投遞，不直接 mutation vendor session store。
- **Worker self-verification**：proposal 與 verified state 分離。
- **Prompt injection/secrets**：adapter/port 邊界需 sanitize；本階段只承載 structured fields。

## Rollback

本階段不連接 production scheduler。可回退 feature commit；已發布的治理文件以 rejected/superseded 狀態保留，不刪除歷史。
