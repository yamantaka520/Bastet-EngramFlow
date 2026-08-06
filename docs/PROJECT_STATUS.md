---
id: STATUS-001
title: Bastet-EngramFlow 專案狀態
type: status
status: active
owner: project-maintainers
created: 2026-08-05
updated: 2026-08-06
---

# Bastet-EngramFlow 專案狀態

- 最後更新：2026-08-06 09:41 CST（UTC+8）
- 已完成階段：`STAGE-000` Runtime-neutral foundation
- 已完成階段：`STAGE-001` Scheduled execution reconciliation core
- 已完成階段：`STAGE-002` Durable reconciliation delivery
- 已完成階段：`STAGE-003` Hermes production reconciliation hook integration
- 已完成階段：`STAGE-004` production SHA reconciliation and rollout readiness
- 已完成階段：`STAGE-005` Bastet Hermes controlled production rollout
- 已完成階段：`STAGE-006` reconciliation outbox shadow inspection
- 已完成階段：`STAGE-007` fail-closed reconciliation dispatcher readiness
- 已完成階段：`STAGE-008` fail-closed Hermes context consumer readiness
- 目前階段：`STAGE-009` Hermes context consumer production artifact readiness（accepted）
- 目前狀態：repository artifacts維持ACCEPT；2026-08-06受控production rollout完成單筆dispatch後，真實incoming turn在hook前被AGY executable trust-pin mismatch阻擋，queue fail-closed且必要rollback完成；production deployment仍WITHHELD
- 工作分支：`feat/hermes-production-reconciliation-hook`
- Foundation commits：`ee4dc13afaf9ebf293dcfea848979b3762687cd8`、`4958b501869050b5bdbec33d299cbafc8cb87116`

## Active Goals

- [GOAL-001](goals/GOAL-001-runtime-neutral-governed-continuation.md)：建立跨 Agent Runtime 的受治理主動專案延續能力。

## Accepted STAGE-009 Deliverables

- [STAGE-009](stages/STAGE-009-hermes-context-consumer-production-artifact-readiness.md)：source-pinned compatibility patch、plugin與production artifact readiness；不構成deployment approval。
- [PLAN-010](plans/PLAN-010-source-pinned-hermes-context-consumer-production-artifacts.md)：只讀preflight、TDD artifacts、digest manifest與canonical runner。
- [EVID-011](evidence/EVID-011-hermes-context-consumer-production-artifact-readiness.md)：live read-back、plugin RED→GREEN、100-test full gate、wheel及source-pinned compatibility evidence。
- [REVIEW-011](reviews/REVIEW-011-stage-009-hermes-context-consumer-production-artifact-readiness.md)：final High 0 / Medium 0 / Low 2 non-blocking；repository artifact readiness ACCEPT、production WITHHELD。
- [RUNBOOK-002](runbooks/RUNBOOK-002-hermes-context-consumer-production-approval.md)：artifact欄位已固定，但production仍為NOT AUTHORIZED。
- [EVID-012](evidence/EVID-012-hermes-context-consumer-production-rollout-attempt.md)：受控deployment、單筆dispatch、AGY prerequisite failure、fail-closed queue與rollback證據。
- [REVIEW-012](reviews/REVIEW-012-stage-009-production-rollout-attempt-closure.md)：rollback execution/evidence closure ACCEPT；因AGY trust prerequisite仍有open High，overall rollout closure與production context consumer enablement WITHHELD，review狀態`blocked`。
- Final production state：context patch/plugin/drop-in/dedicated venv/live delivery DB均已rollback；baseline gateway active且Telegram connected。Source item為`delivered/attempts=1`，matching sink row隔離為`pending/attempts=0`、ambiguous 0，不得自動replay/reset。
- Open blocker：AGY executable實際SHA-256不符合service trust pin；需獨立驗證binary disposition並另行批准，transport connected不可視為agent functional health。

## Accepted STAGE-008 Deliverables

- [STAGE-008](stages/STAGE-008-hermes-context-consumer-readiness.md)：fail-closed Hermes pre-LLM consumer repository readiness；不構成production approval。
- [PLAN-009](plans/PLAN-009-fail-closed-hermes-context-consumer-readiness.md)：exact routing、owner/turn fencing及prepared/sending/delivered/ambiguous狀態機。
- [EVID-010](evidence/EVID-010-hermes-context-consumer-readiness.md)：RED→GREEN、review-fix與production source/service只讀read-back。
- [REVIEW-010](reviews/REVIEW-010-stage-008-hermes-context-consumer-readiness.md)：final High 0 / Medium 0 / Low 2 non-blocking，repository ACCEPT、production WITHHELD。
- [RUNBOOK-002](runbooks/RUNBOOK-002-hermes-context-consumer-production-approval.md)：NOT AUTHORIZED的production approval、canary與rollback pack。
- Production boundary：未建立或mutate delivery DB、未套patch、未安裝plugin、未restart service、未claim item或呼叫platform。

## Accepted STAGE-007 Deliverables

- [STAGE-007](stages/STAGE-007-reconciliation-dispatcher-readiness.md)：source outbox到Bastet-owned Hermes queue的repository readiness；不構成production approval。
- [PLAN-008](plans/PLAN-008-fail-closed-reconciliation-dispatcher-readiness.md)：durable idempotent queue、bounded mutation gate、same-inode protection與redacted CLI。
- [EVID-009](evidence/EVID-009-reconciliation-dispatcher-readiness.md)：RED、10項focused GREEN、independent review修復及production no-mutation boundary。
- Production boundary：未執行enable flag、未建立production delivery DB、未claim/ack/fail既有item、未修改或重啟service。

## Accepted STAGE-006 Deliverables

- [STAGE-006](stages/STAGE-006-reconciliation-outbox-shadow-inspection.md)：只觀測dispatch readiness，不claim/ack或呼叫sink。
- [PLAN-007](plans/PLAN-007-read-only-reconciliation-outbox-shadow-inspection.md)：read-only SQLite inspector、bounded redacted CLI與TDD驗證。
- [EVID-008](evidence/EVID-008-reconciliation-outbox-shadow-inspection.md)：RED、8項focused GREEN、review-fix、71-test full gate與production state read-back。
- [REVIEW-008](reviews/REVIEW-008-stage-006-reconciliation-shadow-closure.md)：final ACCEPT，open High/Medium/Low均0。
- Production boundary：沒有安裝wheel、修改config/systemd、建立scheduler或變更outbox state。

## Accepted STAGE-005 Deployment

- [STAGE-005](stages/STAGE-005-bastet-hermes-controlled-production-rollout.md)：production changeset已部署，狀態`accepted`。
- [PLAN-006](plans/PLAN-006-controlled-bastet-hermes-production-deployment.md)：backup、isolated runtime、patch/config/consent、restart、fixture與rollback驗證已完成。
- [EVID-006](evidence/EVID-006-bastet-hermes-production-deployment-preflight.md)：deployment前read-only preflight。
- [REVIEW-006](reviews/REVIEW-006-stage-005-production-deployment-approval-pack.md)：批准包High 0 / Medium 0。
- [EVID-007](evidence/EVID-007-bastet-hermes-controlled-production-rollout.md)：358-test source gate、service/config/consent、gateway fixture origin及dedup production read-back。
- [REVIEW-007](reviews/REVIEW-007-stage-005-production-rollout-closure.md)：final open High 0 / Medium 0；1項治理例外及1項受控維運風險已記錄。
- Runtime：live Hermes venv未污染；test venv位於timestamped backup，bridge使用exact release wheel。
- Production：service active，patch applied，exact hook consent 1筆，private SQLite durable enqueue有效。

## Accepted STAGE-004 Deliverables

- [STAGE-004](stages/STAGE-004-hermes-production-rollout-readiness.md)：production SHA reconciliation與rollout readiness，狀態`accepted`；production deployment未授權。
- [PLAN-005](plans/PLAN-005-hermes-production-rebase-readiness.md)：production-SHA rebase、hermetic E2E、multi-variant artifact與rollback runbook。
- [EVID-005](evidence/EVID-005-hermes-production-rebase-readiness.md)：production variant verifier四態、358項Hermes scoped gate與63項Bastet full gate。
- [REVIEW-005](reviews/REVIEW-005-hermes-production-rebase-readiness.md)：fixture hermeticity與post-apply gate findings已關閉；final High 0 / Medium 0。
- [RUNBOOK-001](runbooks/RUNBOOK-001-hermes-production-post-cron-rollout.md)：production mutation、read-back與rollback操作邊界。
- Production baseline：Hermes `d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`，clean custom branch `feat/agy-cli-oauth-stdin-hardening`。
- Production boundary：production checkout、config、allowlist與service均未修改或重啟。

## Accepted STAGE-003 Deliverables

- [STAGE-003](stages/STAGE-003-hermes-production-reconciliation-hook.md)：pinned Hermes observer hook與durable bridge integration，狀態`accepted`。
- [PLAN-004](plans/PLAN-004-hermes-post-cron-hook.md)：source patch、shell bridge、restart/replay與thread-origin E2E。
- ADR-0005：fail-open `post_cron_job` unified hook + allowlisted shell bridge。
- [EVID-004](evidence/EVID-004-hermes-post-cron-hook.md)：clean apply、211項Hermes integration tests與63項Bastet full gate。
- [REVIEW-004](reviews/REVIEW-004-hermes-post-cron-hook.md)：final High 0 / Medium 0，狀態`accepted`。
- Pinned baseline：Hermes `1072c0725115e9be0491ca4cb0d965b9f5f59874`；patch SHA-256 `2fa36a110d7dcf9a3fb5846ede59c95a5162edbea6f4c792b7026079a7d30c5b`。
- Production boundary：production checkout、config與services均未修改或重啟。

## Accepted STAGE-002 Deliverables

- [STAGE-002](stages/STAGE-002-durable-reconciliation-delivery.md)：SQLite ledger/outbox、lease recovery 與 structured adapter seam。
- [PLAN-003](plans/PLAN-003-durable-reconciliation-delivery.md)：durable enqueue/dispatch、Hermes result mapping、conversation/proposal adapter contracts 與 failure tests。
- ADR-0004：SQLite transactional outbox + at-least-once delivery；sink 必須 idempotent。
- [EVID-003](evidence/EVID-003-durable-reconciliation-delivery.md)：45 tests 與完整 static/docs gates，狀態 `accepted`。
- [REVIEW-003](reviews/REVIEW-003-durable-reconciliation-delivery.md)：三輪 fresh-context review，Final High 0 / Medium 0，狀態 `accepted`。
- Production 邊界：未修改 Hermes `_process_job()`、gateway session、cron service 或 Telegram production routing。

## Accepted STAGE-001 Deliverables

- [STAGE-001](stages/STAGE-001-scheduled-execution-reconciliation.md)：scheduled execution result/finding 回流與 remediation boundary。
- [PLAN-002](plans/PLAN-002-scheduled-execution-reconciliation.md)：reconciliation models、policy、ports、coordinator 與 tests。
- ADR-0003：structured reconciliation event + governed remediation proposal。
- [EVID-002](evidence/EVID-002-scheduled-execution-reconciliation.md)：30 tests 與完整 static/docs gates，狀態 `accepted`。
- [REVIEW-002](reviews/REVIEW-002-scheduled-execution-reconciliation.md)：Final read-back High 0 / Medium 0，狀態 `accepted`。

## Accepted Foundation Deliverables

- [STAGE-000](stages/STAGE-000-foundation.md)：runtime-neutral contract 與治理基線。
- [PLAN-001](plans/PLAN-001-runtime-neutral-foundation.md)：文件治理與 Agent Runtime SPI 第一個工程增量。
- [EVID-001](evidence/EVID-001-runtime-neutral-foundation.md)：19 tests、Ruff、docs checker、compileall、diff 與 audit 證據。
- [REVIEW-001](reviews/REVIEW-001-runtime-neutral-foundation.md)：三輪獨立 read-back，最終無未處理 High/Medium finding。
- ADR-0001：runtime-neutral core + thin runtime adapters。
- ADR-0002：repository-native 文件治理與穩定 ID。

## Foundation Result

- 建立 immutable runtime models、AgentRuntime Protocol、capability registry 與標準錯誤。
- Worker lifecycle 與 independent verification lifecycle 分離。
- Runtime selection 依 capabilities，不依 vendor version 字串。
- 文件治理檢查可偵測 broken ID、broken Markdown link 與無 EVID 的 Supported claim。
- Compatibility matrix 對未完成真實 E2E 的 runtime 不做虛假 Supported 聲明。

## Blockers

- High：Bastet primary provider的AGY executable實際SHA-256與service設定的trust pin不一致，真實incoming turn在`pre_llm_call`前即初始化失敗。不得在context-consumer rollout中更新或繞過pin。
- `REVIEW-012`維持`blocked`；production context consumer enablement與overall rollout closure均WITHHELD。

## Current Risks

- SQLite reference store為單一filesystem/database boundary；NFS/多主機locking與HA尚未宣告支援。
- Source outbox delivery為at-least-once；本次approved source item已`delivered/attempts=1`，matching sink row隔離為`pending/attempts=0`。兩者不得自動reset、replay或合併。
- Hermes run UUID只在單一emitted payload內穩定，不代表跨job re-execution business identity。
- STAGE-009 context consumer production artifacts曾受控部署後rollback；目前production queue、consumer plugin、dedicated venv、drop-in與exact-routing patch均不在live state。
- Production Hermes仍含既有manifest-owned local post-cron patch，而非immutable deployment commit；upstream upgrade前必須先做verifier、changed-path及rollback preflight。
- Remediation proposal只入queue，不代表已批准、已執行或已驗證。

## Next Gate

先獨立驗證AGY executable來源、版本與digest disposition，並另行批准恢復舊binary或更新trust pin。該prerequisite關閉後，若仍要重試STAGE-009 production enablement，必須建立新的maintenance window、重新決定已ack source與quarantined pending sink的per-item disposition，重跑RUNBOOK-002全部preflight與agent-functional-health gate，並取得新的明確canary/rollback授權。
