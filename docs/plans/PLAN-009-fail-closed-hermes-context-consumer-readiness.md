---
id: PLAN-009
title: Implement fail-closed Hermes context consumer readiness
type: plan
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-008
related_adrs:
  - ADR-0004
  - ADR-0005
related_evidence:
  - EVID-010
---

# PLAN-009 — Fail-closed Hermes Context Consumer Readiness

## Goal

在不觸碰production queue或service的前提下，完成可測試的Hermes context consumer、兩階段delivery狀態機及production approval/rollback設計。

## Implementation

1. 只讀盤點STAGE-007 queue schema、Hermes hook seam與production service ownership。
2. 對`hermes_context_inbox`additive新增state、attempt、lease與transition timestamps；保留既有event identity、payload與receipt。
3. 以`BEGIN IMMEDIATE`實作exact-target claim及`pending → prepared`。
4. 實作owner/turn-fenced `prepared → sending → delivered/ambiguous` transitions。
5. Claim前回收expired leases：prepared回pending；sending轉ambiguous且永不自動retry。
6. 實作`HermesPreLLMContextConsumer.pre_llm_call()`；routing不完整時零claim。
7. 將canonical payload包成escaped untrusted context；不回傳routing IDs、不記錄raw exception。
8. 以legacy STAGE-007 fixture驗證additive migration，含未consume與已consume rows。
9. 建立未授權的production approval/rollback pack；不建立或套用live patch。

## Hermes Compatibility Design

Production source的`agent/turn_context.py`已向`pre_llm_call`傳入`turn_id`。未來經批准的最小backward-compatible patch只能新增：

```python
conversation_id=getattr(agent, "_chat_id", None),
thread_id=getattr(agent, "_thread_id", None),
```

不得以`sender_id`推測conversation，不得偽造incoming user event，也不得直接修改Hermes session DB。Patch必須在pinned source的isolated clone套用、測試、計算digest並經獨立review；STAGE-008不產出可直接部署的production patch。

## Verification

- Focused RED→GREEN unittest。
- STAGE-007 dispatcher regression suite。
- Ruff format/check與compileall。
- Full repository tests與documentation governance。
- Fresh-context independent security/concurrency/migration review。
- Git diff review、commit、push及remote SHA read-back。

## Production Boundary

允許：repository code/docs、temporary SQLite tests、production service/source只讀盤點。

禁止：production DB create/mutation、dispatcher/consumer enable、plugin install/config、Hermes source patch、service restart、platform send及proposal execution。

## Rollback

Repository rollback為revert STAGE-008 commit。因本Plan不做production mutation，沒有live rollback動作。未來production enablement只能依[RUNBOOK-002](../runbooks/RUNBOOK-002-hermes-context-consumer-production-approval.md)執行，且ambiguous item不得在rollback或roll-forward時自動重送。
