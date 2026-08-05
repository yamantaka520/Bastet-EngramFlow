---
id: STAGE-004
title: Hermes production SHA reconciliation and rollout readiness
type: stage
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_plans:
  - PLAN-005
related_adrs:
  - ADR-0005
---

# STAGE-004：Hermes production SHA reconciliation and rollout readiness

## Objective

將STAGE-003 source-pinned integration安全rebase到實際Bastet production Hermes SHA，建立可驗證、可回滾的deployment artifact與runbook；本Stage在明確deployment approval前不修改production checkout/config/service。

## Discovered production baseline

- Service：`hermes-bastet.service`，目前active/running。
- Checkout：`/home/bastet/.hermes/hermes-agent`。
- Branch：`feat/agy-cli-oauth-stdin-hardening`。
- Commit：`d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`。
- Checkout：clean。
- Config：`/home/bastet/.hermes/config.yaml`，owner `bastet:bastet`、mode `0600`。
- Shell-hook allowlist：目前不存在。
- 舊STAGE-003 patch對此SHA的scheduler/plugin hunks均不適用。

## Scope

1. 在production checkout的隔離clone重建source-pinned patch。
2. 以新版module-level `run_one_job()`整合observer hook，涵蓋built-in tick與external provider。
3. 使用durable `execution_id`作單次run identity，不新增隨機UUID。
4. 保留interruption、claim、finish_execution、agent teardown與fail-open語義。
5. 驗證Bastet strict bridge、original-thread routing、restart/replay與artifact basename治理。
6. 建立production rollout/rollback checklist與exact config/allowlist changeset。

## Explicit non-scope without new approval

- 不套patch到`/home/bastet/.hermes/hermes-agent`。
- 不修改`/home/bastet/.hermes/config.yaml`或shell hook allowlist。
- 不restart/stop `hermes-bastet.service`。
- 不觸發真實Telegram delivery。
- 不建立或寫入production reconciliation SQLite。

## Acceptance criteria

- Rebasing artifact pin exact production SHA與SHA-256。
- Clean isolated clone可`git apply --check`；applied clone可reverse-check。
- 新版Hermes focused scheduler/plugin/shell/E2E tests通過。
- Bastet full gate及governance gate通過。
- Independent review未留High/Medium finding。
- Evidence明確區分readiness accepted與production deployment未執行。

## Deployment approval gate

實際deployment需使用者另行明確核准以下完整changeset：production backup/snapshot、patch apply、dedicated venv/SQLite path、exact shell-hook allowlist、service restart、Telegram read-back與rollback演練。
