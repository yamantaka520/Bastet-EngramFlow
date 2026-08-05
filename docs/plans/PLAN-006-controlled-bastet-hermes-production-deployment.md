---
id: PLAN-006
title: Controlled Bastet Hermes production deployment and rollback verification
type: plan
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-005
related_adrs:
  - ADR-0005
related_evidence:
  - EVID-006
  - EVID-007
---

# PLAN-006：Controlled Bastet Hermes production deployment and rollback verification

## Problem

STAGE-004只接受production-SHA rollout readiness，production尚未安裝bridge、套patch、設定hook或驗證真實thread delivery。實際deployment會修改source/config/systemd並restart gateway，因此必須以exact approval、短maintenance window、可重現post-apply tests及immediate rollback控制風險。

## Work packages

1. **Approval capture**
   - 固定Bastet-EngramFlow release SHA、maintenance window、rollback operator、fixture cron job與原thread。
2. **Backup and isolated runtimes**
   - 建立mode `0700` timestamped backup。
   - 備份config、allowlist（若存在）、systemd unit/drop-ins及source metadata。
   - 建立isolated test venv與bridge venv；不修改live Hermes venv dependencies。
3. **Source deployment gate**
   - 停止service、確認inactive及HEAD/clean state未漂移。
   - 套exact patch，要求verifier `applied`及manifest-only changed paths。
   - 使用isolated test venv跑target-tree gate。
4. **Bridge and consent configuration**
   - 安裝exact Bastet release artifact。
   - 建立專屬mode `0700` state子目錄與SQLite path。
   - 新增exact hook command、DB env drop-in及command-scoped consent。
5. **Restart and live read-back**
   - daemon-reload（僅drop-in變更時）、啟動service、確認新PID及health。
   - 執行一個fixture cron job，驗證ledger/outbox/thread routing/log。
   - replay同一payload驗證dedup。
6. **Rollback verification and closure**
   - 任何trigger成立立即rollback。
   - 即使成功，也要驗證reverse-check、備份checksum及rollback命令可執行。
   - 產出EVID-007、REVIEW-007、status及remote read-back。

## Deliverables

- Timestamped production backup manifest。
- Exact source/config/systemd/consent changeset。
- Isolated test與bridge runtime metadata。
- Production post-apply test output及service read-back。
- Fixture execution、dedup與original-thread evidence。
- Rollback evidence、EVID-007與REVIEW-007。

## Acceptance criteria

- 所有STAGE-005 exit criteria均有tool output或read-back支持。
- 不以service active或agent自述單獨宣稱成功。
- Config與logs證據不包含secret、raw prompt或production payload。
- Independent review未留High/Medium finding。
- Production與repository狀態均可由committed evidence重建。

## Risks

- Hook/source錯誤可能阻止gateway正常處理排程。
- Consent過寬可能允許非預期command。
- SQLite path/ownership錯誤可能造成hook fail-open而沒有durable return。
- Fixture選擇錯誤可能觸發非預期production side effect。
- Live venv污染會增加rollback範圍；因此tests與bridge必須使用dedicated venv。

## Verification

依`RUNBOOK-001`執行，核心stop conditions為：HEAD/dirty drift、patch state非預期、changed path超出manifest、target tests失敗、service不active、duplicate outbox、thread routing遺失或consent超範圍。

## Outcome

- 使用者已明確批准完整changeset、maintenance window、rollback operator及目前Telegram DM fixture target。
- Timestamped backup、isolated test runtime、exact release bridge wheel、source patch、config/consent/state/systemd、restart與production read-back已完成。
- 358-test target gate、gateway fixture origin及same-payload dedup均通過。
- Initial stop-state mismatch觸發rollback trap並成功恢復service/source，提供實際可逆性證據。
- 詳細結果與兩次未被誤認為成功的fixture diagnostic attempt見EVID-007。
