---
id: STAGE-002
title: Durable reconciliation delivery
type: stage
status: accepted
owner: project-maintainers
created: 2026-08-05
updated: 2026-08-05
stage_order: 2
related_goals:
  - GOAL-001
related_plans:
  - PLAN-003
---

# STAGE-002：Durable reconciliation delivery

## Purpose

將 STAGE-001 的 process-local reconciliation core 提升為可跨 restart、多 worker claim 與 partial-failure retry 的 durable delivery substrate，並定義 Hermes cron result 與 conversation ingress 的 thin adapter contract。

## Entry Criteria

- STAGE-001 已 accepted，且 stable run/event/proposal IDs 已定義。
- 已以 Hermes source 確認 cron `_process_job()` 可取得 execution result、output file 與 delivery error。
- 已確認不得用 `gateway.mirror.mirror_to_session()` 作為可靠核心，因其 best-effort 且直接 mutation vendor transcript store。

## Deliverables

1. SQLite run ledger 與 event/proposal outbox。
2. Atomic enqueue、idempotency conflict detection、lease claim、ack/fail 與 expired lease recovery。
3. Durable reconciliation service，保證 stable decision enqueue 與 at-least-once dispatch。
4. Hermes cron structured result mapper 與 conversation/proposal sink adapter contract。
5. Restart、duplicate、partial success、lease recovery、payload limit 與 redaction contract tests。
6. Architecture、security、traceability、evidence 與 independent review 更新。

## Exit Criteria

- 同一 `(schedule_id, run_id)`、相同 payload 跨 restart 只建立一組 outbox items。
- 同 key 不同 payload 明確拒絕為 idempotency conflict。
- Worker crash 後 expired lease 可由另一 worker reclaim。
- Sink 成功但 ack 前 crash 可能重送；文件與 API 明確標示 at-least-once，sink contract 必須 idempotent。
- Event 成功、proposal 失敗時只重試 proposal，不重送已 ack event。
- Hermes ingress 不 import 或寫入 Hermes private session database。
- Full tests、docs governance、static checks 與 independent review 通過。

## Risks

- 將 SQLite 錯稱為無條件 multi-host distributed exactly-once。
- Lease 太短造成同一 item concurrent delivery。
- Sink 成功、ack 失敗造成 duplicate external delivery。
- Untrusted cron output 夾帶 secrets、prompt injection 或超大 payload。
- Adapter 誤用 vendor mirror API 破壞 conversation ordering。
