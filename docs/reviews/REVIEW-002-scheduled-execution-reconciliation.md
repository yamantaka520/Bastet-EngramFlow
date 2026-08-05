---
id: REVIEW-002
title: Scheduled execution reconciliation 獨立審查
type: review
status: accepted
owner: independent-reviewer
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-001
related_plans:
  - PLAN-002
related_adrs:
  - ADR-0003
related_evidence:
  - EVID-002
---

# REVIEW-002：Scheduled execution reconciliation 獨立審查

## Review Scope

- `src/bastet_engramflow/reconciliation/`
- `tests/test_scheduled_reconciliation.py`
- STAGE-001、PLAN-002、ADR-0003
- Architecture、project plan/status、security、threat model、traceability updates

## Round 1 Findings

### Code/Security reviewer

- High：0。
- Medium 1：proposal sink 在 inbox success 後失敗的 partial-success retry 未有對稱測試，安全性依賴 idempotent sink contract。
- Medium 2：dedup 只在 process-local coordinator instance 生效，文件不得宣稱 system-wide exactly-once。
- Medium 3：metadata 只做 shallow freeze，nested mutable value 可在建立後被改變。
- Low：lock 包住 sink I/O，保守但會限制吞吐；public event/proposal invariant 可後續強化。

### Architecture/Governance reviewer

- High：0。
- Medium：治理鏈尚缺 EVID-002 / REVIEW-002。
- Low：提醒排除 `__pycache__` 等 repository hygiene noise。
- 正向結論：需求覆蓋、文件/實作一致性及 production/session integration 邊界均保守，未過度宣稱。

## Remediation

1. 新增 `test_proposal_sink_failure_retries_with_stable_idempotent_ids`，證明 inbox 已成功而 proposal sink 首次失敗時，重試使用相同 event/proposal IDs；logical sink records 不重複。
2. Architecture、ADR、Plan、Stage、Project Plan 與 coordinator docstring 明確限定 reference dedup 為 process-local；production durable ledger/outbox 保留為後續工作。
3. Metadata 改為 recursive immutable snapshot，並以先失敗後通過的 test 證明。
4. 建立 EVID-002 與 REVIEW-002，補齊治理鏈。
5. 最終完整 suite 增為 30 tests，Ruff/docs checker/compileall/diff check 全通過。

## Residual Risks

- Production durable inbox/outbox 與 multi-instance claim/commit protocol 尚未實作。
- Sink adapter 的 idempotency 必須由真實 contract/E2E test 證明。
- Coordinator 目前序列化 sink I/O，若追求高吞吐需 keyed lock 或 durable worker queue。
- Platform adapter 必須把 scheduled content 當 untrusted data，實作 redaction、size limit 與 provenance rendering。

## Final Read-back

Fresh-context reviewer 重新檢查完整 implementation、tests 與治理 diff，確認 partial-success retry、process-local/production 邊界、deep immutability 與 evidence/review chain 均已修正；沒有新的 correctness、security 或 governance High/Medium finding。

## Current Decision

`accepted`。High：0；Medium：0。接受範圍為 reference reconciliation core 與文件治理，不構成 production durable delivery/exactly-once 聲明。
