---
id: EVID-008
title: Reconciliation outbox shadow inspection implementation evidence
type: evidence
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-006
related_plans:
  - PLAN-007
related_adrs:
  - ADR-0005
---

# EVID-008 — Reconciliation Outbox Shadow Inspection

## Environment

- Repository: `/mnt/nas/Hermes-Gitlab/Bastet-EngramFlow`
- Branch: `feat/hermes-production-reconciliation-hook`
- Starting commit: `bcc557f124ab077228eb1b0095e73ad0c8f35cbe`
- Production DB: `/home/bastet/.hermes/state/bastet-engramflow/reconciliation.sqlite3`
- Evidence timestamp: 2026-08-05 17:25:55 CST（UTC+8）

## RED

Command:

```bash
PYTHONPATH=src:. python3 -m unittest tests.test_reconciliation_shadow -v
```

Result: exit `1`。ImportError明確指出`SQLiteOutboxShadowInspector`尚不存在，符合預期RED，沒有其他測試失敗。

## GREEN Focused Gate

Implemented artifacts:

- `src/bastet_engramflow/reconciliation/shadow.py`
- `src/bastet_engramflow/reconciliation/shadow_cli.py`
- `tests/test_reconciliation_shadow.py`
- Public exports及`bastet-reconciliation-shadow`console script。

Command:

```bash
ruff format --check <shadow files>
ruff check <shadow files>
PYTHONPATH=src:. python3 -m unittest tests.test_reconciliation_shadow -v
```

Result: exit `0`，3 files formatted，lint PASS，8 tests PASS。

Covered assertions:

- Read-only inspection保留outbox dataclass state。
- Durable DB/WAL bytes不變；transient SQLite `-shm` reader lock不列為durable mutation。
- Raw summary/finding/conversation ID/thread ID/remediation key不出現在report。
- Expired lease只被標記eligible，不reclaim、不增加attempts。
- Proposal在同run event delivered前保持blocked。
- Missing DB fail closed且不建立檔案。
- CLI subprocess成功與錯誤路徑均無traceback。
- Routing corruption有明確aggregate signal。

## Rejected SQLite Modes

Read-only hardening實測：

- `mode=ro&nolock=1`：無法開啟WAL-backed DB。
- `mode=ro&immutable=1`：看不到仍在WAL中的schema/data，回報`no such table`。

因此採用`mode=ro`＋`PRAGMA query_only`。此模式不改DB/WAL或outbox state，但SQLite reader可更新transient `-shm` lock metadata。

## Independent Review Round 1

Fresh-context review判定High 0 / Medium 1 / Low 1：

- Medium：原實作用single-state dict判斷proposal eligibility；同run若有多個event，後值可能覆蓋undelivered state，與store `NOT EXISTS any undelivered event`語義不等價。
- Low：文件宣稱routing corruption aggregate有覆蓋，但尚未有直接corruption fixture。

修復採TDD：新增同run多event regression，RED實測`eligible=2`；改用`runs_with_undelivered_events`集合後GREEN為`eligible=1`且proposal blocked。另新增缺conversation ID的corrupt routing fixture，驗證`routing_errors=1`且不洩漏identifier。修復後shadow focused suite為8 PASS。

## Production Read-only Preflight

Command使用repo source與existing Bastet bridge Python執行shadow CLI，沒有安裝wheel、修改config/systemd或呼叫sink。

Observed report:

- `read_only=true`
- `total=1`
- `pending=1`
- `eligible=1`
- `events=1`
- `proposals=0`
- `routing_errors=0`
- Candidate kind/state：`event` / `pending`
- Target platform：`telegram`
- Thread present：`false`，符合目前DM origin

Authoritative before/after state read-back：

- State：`pending`
- Attempts：`0`
- Lease owner：empty
- Lease deadline：`0`

初次使用DB/WAL digest作單一gate時因SQLite WAL checkpoint/reader lifecycle導致shell comparison exit `1`且無stdout；拆分診斷確認CLI exit `0`、outbox state未改。此嘗試不被誤報為完整PASS，final acceptance以state/attempts/lease及controlled test中的durable byte checks共同支持。

## Closure

- Full repository gate：Ruff format PASS、Ruff lint PASS、71 tests PASS、documentation governance PASS、compileall PASS、diff check PASS。
- [REVIEW-008](../reviews/REVIEW-008-stage-006-reconciliation-shadow-closure.md)：final ACCEPT，open High/Medium/Low均0。
- Commit、push與remote SHA read-back於publication closure執行並回報。
