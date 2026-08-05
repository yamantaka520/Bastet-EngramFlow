---
id: REVIEW-003
title: Durable reconciliation delivery 獨立審查
type: review
status: accepted
owner: independent-reviewer
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
related_evidence:
  - EVID-003
---

# REVIEW-003：Durable reconciliation delivery 獨立審查

## Review Scope

- SQLite run ledger、persisted decision 與 event/proposal outbox。
- Lease claim、expired recovery、owner-bound ack/fail 與 at-least-once crash window。
- Canonical JSON serializer/deserializer 與 byte bounds。
- Hermes cron result mapper、conversation ingress/proposal queue adapter contracts。
- STAGE-002、PLAN-003、ADR-0004、architecture/security/threat/status/traceability 文件。

## Round 1 Findings

- High：0。
- Medium 1：duplicate receipt 在 policy/config drift 後可能與 persisted outbox decision 不一致。
- Medium 2：整體 canonical durable payload 無明確 byte limit。
- Medium 3：active STAGE-002／PLAN-003 未出現在 PROJECT_STATUS，full governance test 失敗。
- Low：Stage front matter 前導空白。

## Round 1 Remediation

1. Persist `decision_json`，duplicate decode/read-back 原 decision；新增 policy drift regression。
2. 新增 configurable `max_payload_bytes` 與 `PayloadTooLargeError`，run/event/proposal 寫入前 fail closed。
3. 更新 PROJECT_STATUS、TRACEABILITY、architecture、security、threat model、README 與 compatibility boundary。
4. 修正 front matter 格式。

## Round 2 Findings

- High：0。
- Medium 1：`decision_json` 本身未套 byte limit，payload bound 尚未完全閉環。
- Low：clean-root pytest import path 不成立；repository 正式 gate 為 unittest + `PYTHONPATH=src:.`。

## Round 2 Remediation

- `decision_json` 加入獨立 byte limit。
- 新增可區分 constituent payload 與 combined decision 的 regression test：700B limit 下 run/event/proposal 可通過、decision 被明確拒絕。
- Full documented gate：45 tests、Ruff、docs checker、compileall、diff check 全部通過。

## Final Read-back

Final fresh-context reviewer 檢查完整 current diff，確認：

- persisted decision drift 已閉環；
- run/decision/event/proposal byte limits 已閉環；
- transaction、lease/recovery、ordering 與 stale-owner semantics 符合 at-least-once contract；
- Hermes seam 沒有 private vendor import/session mutation；
- 文件沒有 exactly-once 或 production-wired 過度宣稱。

最終 finding：

- High：0。
- Medium：0。
- Low 1：sink receipt/exception text 尚無獨立 byte cap，可在後續 hardening 補強。
- Low 2：PROJECT_STATUS 需在 closure 時由 active 改 accepted。

## Current Decision

`accepted`。Final code/doc review High 0 / Medium 0；完整 accepted-tree gate 通過後以 commit read-back 作最終版本證據。接受範圍不包含 Hermes production hook、exactly-once 或多主機 HA。
