---
id: PLAN-004
title: Hermes post-cron hook 與 Bastet durable bridge
type: plan
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-003
related_adrs:
  - ADR-0005
related_evidence:
  - EVID-004
---

# PLAN-004：Hermes post-cron hook 與 Bastet durable bridge

## Objective

以 pinned-source patch 為 Hermes scheduler增加 observer-only `post_cron_job` lifecycle event，復用既有 Python plugin與 allowlisted shell hook infrastructure；由 thin bridge將 bounded structured payload轉成 STAGE-002 envelope並 durable enqueue，全程不直接寫 Hermes session database。

## Scope

### In scope

- Exact Hermes commit compatibility pin與 isolated worktree verification。
- `VALID_HOOKS`、hook CLI synthetic payload與 `_process_job()` single-fire observer call。
- Hook payload schema/version、stable schedule/run identity、origin與 delivery state。
- Shell bridge stdin parser、config/env validation、redaction、payload bounds與 exit codes。
- SQLite receipt/error bound與 scheduler→bridge→outbox integration fixture。
- Patch apply/check/reverse-check、rollback與 drift detection。

### Out of scope

- 直接修改目前 dirty production Hermes checkout。
- 自動重啟 `hermes-neo.service` 或任何 production bot。
- Exactly-once external delivery。
- 直接寫入 Hermes transcript/session store。
- 將 SQLite放在一般 NFS作 multi-host queue。
- 自動執行 remediation proposal。

## Work Items

1. `DOC-09`：建立 STAGE-003、PLAN-004、ADR-0005並 pin compatibility baseline。
2. `TST-05`：先建立 post-cron hook source contract與 fail-open tests。
3. `IMP-09`：建立 pinned Hermes patch artifact與 apply verifier。
4. `TST-06`：先建立 bridge parser、redaction、bounds、duplicate/restart integration tests。
5. `IMP-10`：實作 Bastet shell bridge與 bounded receipt/error hardening。
6. `INT-03`：在 exact-commit worktree apply patch並執行 focused Hermes tests。
7. `INT-04`：執行 scheduler fixture→shell hook→SQLite ledger/outbox E2E。
8. `DOC-10`：更新 architecture、security、threat model、compatibility、traceability與status。
9. `EVID-04`／`REV-04`：保存驗證證據並完成獨立 review/remediation。

## Acceptance Criteria

1. Patch僅能套用 exact pinned commit或在 preflight 明確拒絕 drift。
2. Hook在 cron persistence後 single-fire；無 hook時行為等同 baseline。
3. Python/shell hook exception、timeout或 malformed stdout不改變 cron success/failure狀態。
4. Hook payload具有 schema version，且不傳 raw job prompt、credentials或完整 unbounded output。
5. Bridge只接受 JSON object與已知 schema，缺少 identity/origin欄位時 typed failure且不建立 partial ledger。
6. Bridge enqueue成功可由另一 process/restart讀回；duplicate為 idempotent，conflict拒絕。
7. Sink receipt/error具 bounded UTF-8 persistence contract。
8. Original platform/chat/thread/session metadata可從 fixture read-back。
9. Pinned Hermes focused tests與Bastet full tests通過。
10. Production deployment保持未執行，文件包含安裝、read-back與 rollback步驟。

## Verification

- `python -m unittest discover -s tests -v`
- `python scripts/check_docs.py`
- `ruff format --check .`
- `ruff check .`
- `python -m compileall -q src scripts tests integrations`
- `python integrations/hermes/verify_patch.py --hermes-tree /tmp/hermes-reconciliation-1072c`
- pinned Hermes focused tests
- `git diff --check`

## Rollback

在 isolated tree以 `git apply -R --check`驗證 patch可逆；production deployment時必須先 snapshot exact source/config、停止 scheduler intake、套用 patch、跑 smoke test再重啟。任一 read-back失敗即停服、reverse patch、恢復 config並重跑 baseline cron test。此 stage本身不執行 production rollout。
