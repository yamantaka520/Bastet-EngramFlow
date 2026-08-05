---
id: PLAN-005
title: Hermes production SHA rebase and isolated readiness validation
type: plan
status: active
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-004
related_adrs:
  - ADR-0005
---

# PLAN-005：Hermes production SHA rebase and isolated readiness validation

## Problem

STAGE-003 artifact pin在Hermes `1072c072...`，而實際Bastet production checkout為clean custom branch SHA `d0c0a6b...`。舊patch的`cron/scheduler.py`與`hermes_cli/plugins.py` hunks均無法套用；直接部署會失敗且可能覆蓋新版execution/interruption語義。

## Work packages

1. **Production discovery**
   - Read-only確認service owner、checkout、SHA、dirty state、config mode與hook allowlist。
2. **Source reconciliation**
   - 只在`/tmp`隔離clone修改。
   - 將hook移至新版共用`run_one_job()`。
   - 以`execution_id`作`run_id`。
3. **Artifact and verifier**
   - 產生production-SHA專用patch/manifest。
   - 驗證apply、reverse-check、digest與README一致性。
4. **Focused E2E**
   - built-in tick與direct `run_one_job()`路徑。
   - success、soft failure、delivery failure、exception、interruption與hook fail-open。
   - shell subprocess → Bastet CLI → isolated SQLite、restart/replay與thread origin。
5. **Governance closure**
   - EVID-005、REVIEW-005、compatibility/status更新。
   - commit、push及remote read-back。

## Safety controls

- Production checkout只讀；所有source修改在isolated clone。
- 不輸出config或allowlist secret內容。
- Patch artifact由Git直接寫檔，不經redaction tool-output round trip。
- 不用fuzzy apply或whitespace ignore掩蓋版本漂移。
- Production deployment作為後續獨立approval gate。

## Verification commands

```bash
python3 integrations/hermes/verify_patch.py --manifest integrations/hermes/production-d0c0a6b/manifest.json --hermes-tree <clean-clone> --expect applicable
python3 -m pytest <focused-hermes-fixtures> -o 'addopts=' -q
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
python3 scripts/check_docs.py
```

## Deliverables

- `integrations/hermes/production-d0c0a6b/manifest.json`
- `integrations/hermes/production-d0c0a6b/post-cron-job-hook.patch`
- Production-SHA focused fixtures與E2E harness
- Rollout/rollback runbook（未執行）
- EVID-005與REVIEW-005
