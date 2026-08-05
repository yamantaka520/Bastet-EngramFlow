---
id: STAGE-009
title: Hermes context consumer production artifact readiness
type: stage
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_plans:
  - PLAN-010
related_adrs:
  - ADR-0004
  - ADR-0005
related_evidence:
  - EVID-011
---

# STAGE-009 — Hermes Context Consumer Production Artifact Readiness

## Objective

將STAGE-008已接受的fail-closed consumer固定為可審查的source-pinned Hermes compatibility patch、user plugin artifact、digest manifest與canonical compatibility runner；完成production只讀preflight與approval boundary，但不套用production patch、不安裝plugin、不建立delivery DB、不claim queue、不restart service。

## Scope

- 固定Hermes base commit與只允許`agent/turn_context.py`的兩行routing patch。
- 建立`bastet-context-consumer` user plugin artifact。
- plugin註冊前以read-only SQLite連線驗證既有DB、完整schema、index、owner與`0600`；不存在或未初始化時不得建立或migration。
- 建立artifact SHA-256 manifest、applicable/applied verifier及source-pinned test runner。
- 以真實Hermes`PluginManager`執行plugin load與exact-routing test。
- 只讀核對live service/source/filesystem/outbox state及既有patch drift。
- 更新production approval/rollback pack的已知輸入與未決欄位。

## Explicit Non-Goals

- 不修改`/home/bastet/.hermes/hermes-agent`。
- 不建立`BASTET_HERMES_DELIVERY_DB`或執行任何queue constructor於production path。
- 不安裝wheel或plugin，不修改Hermes config/systemd drop-in。
- 不啟用dispatcher/consumer，不claim/ack/requeue既有pending item。
- 不restart`hermes-bastet.service`，不觸發真實conversation canary或platform API。
- 不將repository acceptance解讀為production mutation approval。

## Safety Invariants

1. Compatibility patch changed-path集合必須精確等於`agent/turn_context.py`。
2. Patch只傳遞`agent._chat_id`與`agent._thread_id`，不得使用`sender_id`推測conversation。
3. Plugin缺必要環境、相對/不存在/非regular DB、不相容schema、owner不符或非`0600`時不得註冊hook。
4. Plugin preflight不得建立或migration delivery DB。
5. Live dirty paths必須精確等於既有governed bridge patch；任何額外path為stop condition。
6. 既有source outbox pending item不得被bulk implicit adoption；canary前需逐筆書面處置。
7. Production deployment、backup、restart與canary仍需獨立明確批准。

## Acceptance Criteria

- Plugin focused RED→GREEN與真實Hermes PluginManager test通過。
- Unpatched source-pinned routing test為RED；套patch後canonical runner為GREEN。
- Artifact verifier在live tree回報`applicable`，在isolated patched tree回報`applied`。
- Read-only production preflight固定service owner、Hermes HEAD、dirty paths、filesystem與queue counts。
- Ruff format/lint、compileall、documentation governance、canonical repository tests與source-pinned tests全部通過。
- Independent review無open High/Medium finding。
- Commit、push與remote SHA read-back一致。
- Production mutation保持零；approval明確WITHHELD。

## Approval Gate

本Stage只接受deployment artifacts與preflight evidence。任何production mutation仍須另行固定：maintenance window、approver、release wheel digest、backup/restore operators與paths、delivery DB path、existing pending item disposition、single canary target、observation period及rollback authority。任一欄位空白即不得部署。
