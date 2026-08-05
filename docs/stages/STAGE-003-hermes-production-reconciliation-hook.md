---
id: STAGE-003
title: Hermes production reconciliation hook integration
type: stage
status: active
owner: project-maintainers
created: 2026-08-05
updated: 2026-08-05
stage_order: 3
related_goals:
  - GOAL-001
related_plans:
  - PLAN-004
---

# STAGE-003：Hermes production reconciliation hook integration

## Purpose

在不直接 mutation Hermes transcript/session store 的前提下，為 pinned Hermes scheduler 增加 bounded、observer-only、fail-open 的 `post_cron_job` lifecycle hook，並以 allowlisted shell bridge 將 structured cron outcome 原子 enqueue 至 Bastet durable reconciliation ledger/outbox。

## Pinned Baseline

- Hermes commit：`1072c0725115e9be0491ca4cb0d965b9f5f59874`
- Validation worktree：`/tmp/hermes-reconciliation-1072c`
- Production checkout：`/home/neo/.hermes/hermes-agent`，dirty 且與 upstream diverged；本 stage 不直接修改或重啟。
- Hook substrate：Hermes `VALID_HOOKS`、`invoke_hook()` 與 `agent.shell_hooks` allowlist/timeout/JSON stdin protocol。

## Entry Criteria

- STAGE-002 accepted；SQLite ledger/outbox、Hermes mapper 與 adapter contracts 已通過 restart/retry tests。
- 已從 source 確認 `_process_job()` 可取得 execution status、output file、delivery error 與 job origin metadata。
- 已建立 exact-commit detached worktree，避免污染 production checkout。

## Deliverables

1. `post_cron_job` structured payload contract 與 fail-open invocation patch。
2. Pinned Hermes patch artifact、apply/check/reverse-check script與 focused upstream tests。
3. Allowlisted Bastet shell bridge，從 stdin 解析、redact、bound、map 並 durable enqueue。
4. Bounded sink receipt/error hardening與 corresponding regression tests。
5. Scheduler fixture → hook → bridge → SQLite ledger/outbox integration tests。
6. Restart/replay、duplicate、delivery partial failure、thread-origin preservation tests。
7. Compatibility、security、threat model、traceability、evidence與 independent review closure。

## Exit Criteria

- Patch 可 clean apply 至 exact pinned commit，且 reverse check 可驗證安裝狀態。
- Hook 對成功、execution failure、empty response與 delivery failure各只觸發一次。
- Hook callback/shell failure不得改變既有 cron `mark_job_run()` 結果或中斷 tick。
- Payload 不包含 raw secrets，且所有不可信文字具有明確 byte/character bound。
- Bridge duplicate replay 不新增第二組 outbox items；conflict 明確拒絕。
- Original platform/chat/thread/session metadata 保留至 durable envelope。
- 不修改 production checkout、config或 service；部署另需受控 approval/rollback gate。
- Full tests、pinned integration tests、docs governance、static checks與 independent review通過。

## Risks

- Hook 放在 `mark_job_run()` 前造成 plugin failure 改變 cron 狀態。
- Shell bridge timeout 阻塞 scheduler worker過久。
- Hook payload帶出 raw prompt、token或未截斷 output。
- Patch套到非 pinned source造成 silent misplacement。
- Production checkout既有 local changes被覆蓋。
- At-least-once hook replay被誤稱 exactly-once。
