---
id: ADR-0005
title: Use a fail-open Hermes post-cron lifecycle hook with an allowlisted shell bridge
type: adr
status: proposed
owner: architecture
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-003
related_plans:
  - PLAN-004
---

# ADR-0005：以 fail-open Hermes post-cron hook連接 allowlisted shell bridge

## Context

Hermes pinned scheduler的 `_process_job()`已掌握 execution output、final response、saved artifact、delivery error與 job origin，但目前沒有 cron lifecycle hook。Hermes已有 `VALID_HOOKS`、Python plugin callbacks與經 allowlist、timeout、`shell=False`執行的 shell hook bridge。直接從 Bastet import Hermes private scheduler/session module會形成脆弱耦合；直接 mutation transcript store亦違反 ordering與ownership boundary。

## Decision

1. 在 pinned Hermes source增加 observer-only `post_cron_job` lifecycle event。
2. Invocation位於 `mark_job_run()`完成後，並由獨立 `try/except` fail-open包覆。
3. Payload schema固定為 `hermes.post_cron_job.v1`，upstream不依賴Bastet名稱；只包含stable identity、bounded result摘要、artifact path、delivery status與 origin routing metadata，不含 raw prompt或credential。
4. 復用既有 `invoke_hook()`，使Python plugin與 allowlisted shell hook可共存。
5. Production integration首選 shell bridge：process isolation、explicit consent、timeout與JSON stdin contract；bridge只負責 durable enqueue。
6. Bastet durable store保持at-least-once；duplicate external side effect仍由stable ID與idempotent sink處理。
7. Exact source commit與patch digest必須在部署前驗證；drift時拒絕套用。

## Consequences

### Positive

- Hermes core change極小，無consumer時幾乎為no-op。
- Hook failure不污染cron既有status persistence。
- Bridge不需讓Hermes import Bastet private modules。
- Allowlist與timeout復用既有安全治理。

### Negative

- Shell process spawn增加每次cron completion延遲。
- Patch需要隨Hermes upstream drift重新rebase與contract test。
- Hook成功到bridge durable commit間仍可能失敗；需要error visibility與replay。
- At-least-once replay要求ledger與下游sink idempotent。

## Alternatives Rejected

- `gateway.mirror.mirror_to_session()`：best-effort且直接mutation vendor transcript。
- 在Hermes scheduler內直接import Bastet package：耦合dependency與venv lifecycle。
- 讀取cron markdown output目錄輪詢：identity、delivery error與origin context不完整，且race較多。
- 直接修改production checkout後再測：現況dirty且diverged，rollback風險不可接受。

## Status

Proposed；待pinned patch、bridge integration tests與independent review通過後轉Accepted。
