---
id: STAGE-007
title: Fail-closed reconciliation dispatcher readiness
type: stage
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_plans:
  - PLAN-008
related_adrs:
  - ADR-0004
  - ADR-0005
related_evidence:
  - EVID-009
---

# STAGE-007 — Fail-closed Reconciliation Dispatcher Readiness

## Objective

建立source reconciliation outbox到Bastet-owned Hermes delivery queue的durable、bounded、idempotent handoff，使sink成功後source ack前崩潰可安全重播；本Stage只完成repository readiness，不部署production dispatcher、不claim現有production outbox，也不啟用Hermes queue consumer或外部平台delivery。

## Scope

- 提供SQLite-backed `HermesConversationIngress`與`HermesRemediationQueue`實作。
- 以event/proposal ID加canonical payload digest保證重播回傳同一receipt，identity collision則fail closed。
- 提供bounded dispatcher CLI；必須顯式傳入`--enable-dispatch`才可開啟或修改DB。
- Source outbox與delivery queue必須為不同實體檔案；相同path、symlink resolve結果及hardlink inode均拒絕。
- CLI成功與失敗輸出不得包含payload、summary、conversation/thread identifier或任意exception message。
- Event先於同run proposal進入queue；proposal入queue不代表批准、執行或驗證。

## Explicit Non-Goals

- 不修改、安裝或重啟`hermes-bastet.service`。
- 不在production執行`bastet-reconciliation-dispatch --enable-dispatch`。
- 不claim、ack、fail或requeue目前production outbox item。
- 不建立systemd unit、timer或cron dispatcher。
- 不呼叫Telegram或其他platform adapter。
- 不實作Hermes gateway consumer；delivery queue的`consumed_at`在本Stage不變更。
- 不批准或執行remediation proposal。

## Safety Invariants

1. Missing `--enable-dispatch`必須在開啟任何DB前exit 2。
2. Missing source DB不得被constructor意外建立。
3. 同一sink identity及相同canonical payload只能形成一筆queue row與stable receipt。
4. 同identity不同payload必須拋出idempotency conflict，不覆寫既有資料。
5. Source sink-success/ack crash window重播不得產生第二筆queue row。
6. `--max-items`介於1與100，預設1，限制單次mutation blast radius。
7. 同path或same-inode DB在任何dispatch mutation前拒絕。
8. Production rollout需要獨立approval stage、backup、rollback、service ownership與consumer設計；本Stage accepted不構成批准。

## Acceptance Criteria

- RED→GREEN tests涵蓋durable dedupe、collision、oversize、mutation gate、bounded dispatch、missing source、same path、hardlink alias及stderr redaction。
- Focused tests與full repository gates通過。
- Independent review無open High/Medium finding。
- Governance文件明確區分repository readiness與production enablement。
- Commit、push及remote SHA read-back一致。

## Next Gate

建立Hermes gateway queue consumer、systemd/timer ownership、production backup/rollback及現有pending item處置approval pack。未取得明確production approval前，dispatcher與consumer保持disabled。
