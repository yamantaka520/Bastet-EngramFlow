---
id: EVID-006
title: Bastet Hermes production deployment preflight evidence
type: evidence
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-005
related_plans:
  - PLAN-006
related_adrs:
  - ADR-0005
---

# EVID-006：Bastet Hermes Production Deployment Preflight

## Accepted claim

2026-08-05 14:41 CST（UTC+8）的read-only preflight確認production source與service仍符合RUNBOOK-001的固定baseline，production patch仍可乾淨套用。此Evidence只接受preflight結果，不代表production deployment已批准或執行。

## Source and patch state

- Checkout：`/home/bastet/.hermes/hermes-agent`
- Branch：`feat/agy-cli-oauth-stdin-hardening`
- HEAD：`d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`
- Working tree：clean
- Variant：`production-d0c0a6b`
- Patch SHA-256：`af1d421f0b33ee06e14dae9bfca20e4c5490e13c28f78b76dbb9979614cc65dc`
- Live-tree verifier：`state=applicable`，exit code 0
- Bastet service user可讀accepted release checkout與patch artifact。

## Service and runtime state

- Service：`hermes-bastet.service`
- State：active/running
- Main PID at observation：`2164930`
- User：`bastet`
- ExecStart：`/home/bastet/.hermes/hermes-agent/venv/bin/hermes gateway run`
- Runtime：Python 3.11.15
- Unit：`/etc/systemd/system/hermes-bastet.service`
- Existing drop-in：`agy-adapter.conf`
- Root filesystem：600 GB available（32% used）
- NAS filesystem：2.8 TB available（75% used）

## Config and consent baseline

No config contents or secret values were captured.

- `config.yaml` owner/mode：`bastet:bastet` / `0600`
- Size：5685 bytes
- SHA-256：`d9a0eb41807821f7ddcf9060e0f0db2f63c28579f0a0d114417b9ad573763560`
- `hooks`：absent
- `hooks_auto_accept`：absent，effective false
- `shell-hooks-allowlist.json`：absent
- Dedicated bridge venv：absent
- Existing `state/` contains gateway heartbeat；不得整體改mode或替換。
- Dedicated reconciliation path改為新建`state/bastet-engramflow/` mode `0700`。

## Discovered blocker and resolution

Production Hermes venv沒有`pytest`，直接執行`run_variant_tests.py`會以`ModuleNotFoundError`失敗。這不是patch compatibility failure，但在post-apply gate前必須解除。

Approved resolution design：

1. 不在live Hermes venv安裝pytest。
2. 在timestamped backup directory下以production Python 3.11建立isolated test venv。
3. 從exact local production Hermes checkout安裝其pinned `dev` extra。
4. 用該venv執行manifest-selected target-tree tests。
5. Tests完成後保留venv metadata到evidence；其清理不屬於emergency rollback。

Production pyproject的`dev` extra包含pinned pytest；production runtime本身維持不變。

## Unresolved approval inputs

- Approved Bastet-EngramFlow release SHA。
- Maintenance window。
- Named rollback operator。
- 唯一fixture cron job ID/name。
- Fixture的原Telegram conversation/thread target。

## Safety boundary

本preflight沒有：

- 建立backup、venv、state subdirectory或SQLite；
- 套用patch或改動production source；
- 修改config、allowlist、systemd unit/drop-in；
- stop/restart service；
- 觸發cron或Telegram delivery。
