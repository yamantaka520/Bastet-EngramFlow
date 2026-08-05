---
id: EVID-003
title: Durable reconciliation delivery 驗證證據
type: evidence
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-002
related_plans:
  - PLAN-003
related_adrs:
  - ADR-0004
---

# EVID-003：Durable reconciliation delivery 驗證證據

## Scope

驗證 SQLite durable run ledger/outbox、persisted decision、lease claim/recovery、partial-failure retry、canonical payload bounds，以及 Hermes structured cron/inbox/proposal adapter contracts。

## TDD / Remediation Evidence

### RED 1：durable API 尚未存在

```text
PYTHONPATH=src:. python3 -m unittest tests.test_durable_reconciliation -v
ImportError / missing durable reconciliation public API
```

### GREEN 1：SQLite outbox 與 Hermes contracts

初版 targeted suite 12 tests 通過，覆蓋 restart duplicate、conflict、lease expiry、event-before-proposal、partial success、Hermes mapping 與 sanitizer。

### Review remediation

第一輪 review 的 Medium findings：

1. Duplicate 在 policy drift 後可能回傳與 persisted outbox 不一致的新 decision。
2. Canonical durable payload 沒有完整 byte limit。
3. STAGE-002／PLAN-003 未出現在 PROJECT_STATUS。

修正：

- `reconciliation_runs` 同 transaction 保存 canonical `decision_json`；duplicate 讀回原 decision。
- run、decision、event、proposal 分別在 SQLite write 前檢查 UTF-8 byte size；超限以 `PayloadTooLargeError` fail closed。
- 補齊 PROJECT_STATUS、TRACEABILITY、architecture、security、threat model 與 compatibility boundary。
- 第二輪 review 發現 decision payload 尚未獨立限長；以 700-byte regression case 修正：run 577B、event 513B、proposal 473B、decision 1076B。

## Final Reproducible Gate

執行：

```bash
ruff format --check .
ruff check .
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
python3 scripts/check_docs.py
python3 -m compileall -q src scripts tests
git diff --check
```

2026-08-05 09:10 CST 前最後一次結果：

- Ruff format：23 files already formatted。
- Ruff check：All checks passed。
- Unit/governance tests：45 tests，全部通過。
- Documentation governance：PASS。
- Compileall：exit 0。
- Git diff check：exit 0。

## Covered Contracts

1. Ledger + persisted decision + outbox atomic enqueue。
2. 同 run key 同 payload 為 duplicate；不同 payload 為 typed conflict。
3. Policy drift duplicate 回傳已持久化 decision。
4. Run/decision/event/proposal canonical JSON 各自有 byte limit，超限不留下 partial ledger/outbox。
5. Lease 阻擋其他 worker，expired lease 可 recovery，stale owner ack 被拒絕。
6. Event ack 前，同 run proposal 不可 claim。
7. Sink failure 只釋放失敗 item；已 delivered item 不重播。
8. Sink success、ack 前 crash 允許 at-least-once replay；不宣稱 exactly-once。
9. Hermes execution failure、delivery partial、origin/thread、artifact 與 untrusted text mapping。
10. Hermes adapters 僅使用 public structured contracts，不 import private vendor modules或直接 mutation session history。

## Independent Review

- Round 1：High 0 / Medium 3；全部修正。
- Round 2：High 0 / Medium 1（decision_json byte limit）；已修正。
- Final fresh-context read-back：High 0 / Medium 0；建議接受。

## Limitations / Residual Risks

- SQLite reference store 限定單一 database/filesystem boundary；未宣告 NFS、多主機 HA 或 exactly-once。
- Sink receipt 與 exception text 尚未有獨立 byte cap，列為 Low residual storage-growth risk。
- Hermes production `_process_job()`、gateway hook、Telegram delivery/read-back 與 rollback 尚未接線或部署。
- `python3 -m pytest` 不是本 repository 的 acceptance command；正式 gate 為帶 `PYTHONPATH=src:.` 的 unittest discovery。
- 自訂 automated secret-regex script 因執行 consent guard 未執行；final independent diff review 未發現真實 secret exposure。此證據不宣稱該自訂 scan 已通過。
