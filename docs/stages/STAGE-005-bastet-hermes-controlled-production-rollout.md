---
id: STAGE-005
title: Bastet Hermes controlled production rollout
spec_version: "0.1"
type: stage
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_plans:
  - PLAN-006
related_adrs:
  - ADR-0005
---

# STAGE-005：Bastet Hermes controlled production rollout

## Objective

依`RUNBOOK-001`將已接受的`production-d0c0a6b` observer-hook variant部署到Bastet Hermes production，完成exact consent、durable reconciliation、service及原Telegram thread read-back，並實際驗證rollback可用性。

## Entry evidence

- STAGE-004與PLAN-005已accepted。
- Production Hermes HEAD固定為`d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`。
- Production patch SHA-256固定為`af1d421f0b33ee06e14dae9bfca20e4c5490e13c28f78b76dbb9979614cc65dc`。
- 2026-08-05唯讀preflight確認patch state為`applicable`、checkout clean、service active。
- Isolated production-variant gate已有358 tests PASS證據。

## Approved changeset boundary

若取得明確deployment approval，只允許：

1. 建立mode `0700`的timestamped backup與isolated test/bridge venv。
2. 對exact production Hermes HEAD套用manifest-pinned patch。
3. 在isolated test venv執行post-apply 358-test target gate。
4. 建立`/home/bastet/.hermes/state/bastet-engramflow/` mode `0700`及其SQLite檔。
5. 在`config.yaml`加入exact `post_cron_job` command，保持global auto-accept關閉。
6. 建立單一systemd drop-in，只增加`BASTET_RECONCILIATION_DB`。
7. 只批准`post_cron_job`與exact bridge command pair。
8. restart `hermes-bastet.service`並做health/read-back。
9. 只執行一個預先命名的fixture cron job與一次same-payload replay。
10. 若任何rollback trigger成立，立即按RUNBOOK-001回復。

任何額外source、provider、model、credential、routing或production job變更都不在本Stage授權範圍。

## Resolved blockers

- `APPROVAL-001`：使用者明確批准現在執行完整changeset；小NEO為named rollback operator。
- `TEST-RUNTIME-001`：timestamped backup下的isolated test venv通過358 tests；live runtime venv未安裝pytest。
- `FIXTURE-001`：gateway-scheduled `ecca3943fd75`回傳目前Telegram DM `8686567559`，origin及dedup read-back通過。

完整production evidence見[EVID-007](../evidence/EVID-007-bastet-hermes-controlled-production-rollout.md)。

## Exit criteria

- Backup/config/allowlist/unit metadata與checksum已保存。
- Patch verifier在production checkout回報`applied`，changed paths完全符合manifest。
- Isolated test venv的target-tree gate為358 PASS或更新後等價、經審查的完整gate。
- Service restart後active且PID/start timestamp已更新。
- Hook event、Bastet ledger/outbox、dedup replay與original-thread routing read-back通過。
- 無其他production jobs被fixture驗證觸發。
- Rollback演練或可逆性read-back完成且保留audit evidence。
- [REVIEW-007](../reviews/REVIEW-007-stage-005-production-rollout-closure.md)已接受，open High/Medium均為0；治理例外與受控維運風險有明確disposition。
- EVID-007與REVIEW-007完成後，Stage才可轉為accepted。
