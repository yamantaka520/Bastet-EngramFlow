---
id: EVID-002
title: Scheduled execution reconciliation 驗證證據
type: evidence
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-001
related_plans:
  - PLAN-002
related_adrs:
  - ADR-0003
---

# EVID-002：Scheduled execution reconciliation 驗證證據

## Scope

驗證 runtime-neutral scheduled execution reconciliation core：structured conversation return、remediation proposal、policy gates、process-local dedup、partial sink retry 與 immutable data contracts。

## TDD Evidence

### RED 1：package 尚未實作

```text
PYTHONPATH=src:. python3 -m unittest tests.test_scheduled_reconciliation -v
ModuleNotFoundError: No module named 'bastet_engramflow.reconciliation'
```

### GREEN 1：最小 reconciliation core

新增 models、policy、ports、coordinator 後，focused suite 為 9 tests / OK。

### RED 2：巢狀 metadata 不是 immutable snapshot

```text
test_nested_metadata_is_an_immutable_snapshot ... FAIL
AssertionError: ['initial', 'changed'] != ('initial',)
```

### GREEN 2：recursive immutable snapshot 與 partial-success retry

Metadata mapping/sequence/set 分別 snapshot 為 read-only mapping/tuple/frozenset，並補上 proposal sink failure after inbox success 的 stable-ID idempotent retry test。

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

結果：

- Ruff format：17 files already formatted。
- Ruff check：All checks passed。
- Unit/governance tests：30 tests，全部通過。
- Documentation governance：PASS。
- Compileall：exit 0。
- Git diff check：exit 0。

## Covered Contracts

1. Successful run 回流 origin conversation inbox。
2. Failed/retryable/read-only/idempotent finding 只標記 auto-remediation eligible，不直接執行。
3. Critical、external side effect、缺少 idempotency key、depth exhausted 一律 approval required。
4. Proposal created 不等於 problem resolved 或 independently verified。
5. Duplicate run 在單一 coordinator instance 內不重複投遞/提案。
6. Inbox failure 不 local-commit，可重試。
7. Inbox success + proposal sink failure 使用 stable event/proposal IDs 安全重試；sink contract 必須 idempotent。
8. 無 origin conversation 不假造 delivery receipt。
9. Nested metadata 建立遞迴 immutable snapshot。

## Limitations

- Reference coordinator 的 ledger 是 process-local memory；不宣稱跨重啟或多實例 exactly-once。
- Production 仍需 durable ledger/outbox、idempotent platform inbox、proposal queue、redaction/size limit 與 scheduler adapter。
- 本證據已由 final fresh-context read-back 接受；High/Medium findings 為 0。本證據不代表 Hermes 或其他 runtime 的 production integration 已完成。
