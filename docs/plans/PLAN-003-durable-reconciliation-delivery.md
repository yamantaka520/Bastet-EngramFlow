---
id: PLAN-003
title: Durable reconciliation delivery 與 Hermes adapter contract
type: plan
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-002
related_adrs:
  - ADR-0004
related_evidence:
  - EVID-003
---

# PLAN-003：Durable reconciliation delivery 與 Hermes adapter contract

## Objective

以 Python stdlib SQLite 建立 durable run ledger/outbox，將 reconciliation decision 的建立與 delivery state 交易化；提供 runtime-neutral claim/ack/fail worker 與 Hermes cron structured ingress contract，但不直接修改 production scheduler、gateway 或 session store。

## Scope

### In scope

- Canonical serialized decision payload 與 payload digest。
- Atomic run ledger + outbox enqueue。
- Stable outbox item ID、lease owner/deadline、attempt/error/receipt。
- Expired lease recovery、partial success 與 restart tests。
- Hermes cron execution/delivery result → `ScheduledRunEnvelope` mapper。
- Conversation/proposal adapter protocols、redaction 與 bounded text rendering。

### Out of scope

- 直接修改 `/home/neo/.hermes/hermes-agent` 或 production bot config/service。
- 直接呼叫 `gateway.mirror.mirror_to_session()` 修改 transcript。
- SQLite shared over NFS/multi-host deployment guarantee。
- Exactly-once external side effect。
- Proposal queue → real runtime execution 與 production remediation。

## Work Items

1. `DOC-07`：建立 STAGE-002、PLAN-003、ADR-0004。
2. `TST-04`：先建立 durable store/service 與 Hermes mapper 失敗測試。
3. `IMP-06`：實作 SQLite ledger/outbox transaction 與 claim lifecycle。
4. `IMP-07`：實作 durable service 與 structured sink dispatch。
5. `IMP-08`：實作 Hermes cron result mapper、redaction/size contract。
6. `DOC-08`：更新 architecture、security、threat model、traceability 與 status。
7. `EVID-03`：記錄 crash/restart/duplicate/partial success 驗證。
8. `REV-03`：獨立 diff review 與 remediation。

## Acceptance Criteria

1. First enqueue 原子建立 run ledger 與必要 outbox rows。
2. Identical duplicate enqueue 回傳 duplicate；conflicting payload raise typed error。
3. Claim 使用 transaction 與 lease；未過期 lease 不可被其他 worker claim。
4. Expired claim 可 reclaim；attempt count 與 last error 可讀回。
5. Ack/fail 必須綁定 lease owner，stale worker 不可覆蓋新 owner 狀態。
6. Event/proposal partial success 後只重試未完成 item。
7. Restart 後 delivered state 與 duplicate state 保留。
8. Hermes mapper 對 success/failure/delivery failure 產生 deterministic structured envelope，並 redaction、truncate untrusted text。
9. Adapter contract 不 import Hermes private module、不 mutation vendor session store。
10. Full tests、docs checker、Ruff、compileall、secret scan 與 independent review 通過。

## Verification

- `python -m unittest discover -s tests -v`
- `python scripts/check_docs.py`
- `ruff format --check .`
- `ruff check .`
- `python -m compileall -q src scripts tests`
- `git diff --check`

## Reliability Contract

- Storage：single SQLite database，WAL，busy timeout，foreign keys。
- Queue：at-least-once；sink 以 stable event/proposal ID 實作 idempotency。
- Claim：lease-based，ack/fail compare owner。
- Crash window：sink success 到 ack 之間 crash 會重送；不得宣稱 exactly-once。
- Multi-host：不支援將 SQLite DB 放在一般 NFS 當 distributed queue。

## Rollback

本階段不連接 production scheduler。可停止 dispatcher 並回退 feature commit；SQLite ledger/outbox 保留作 audit，不假裝已發送事件消失。
