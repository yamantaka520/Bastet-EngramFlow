---
id: REVIEW-011
title: STAGE-009 Hermes context consumer production artifact readiness review
type: review
status: accepted
owner: independent-review
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-009
related_plans:
  - PLAN-010
related_evidence:
  - EVID-011
---

# REVIEW-011 — STAGE-009 Hermes Context Consumer Production Artifact Readiness

## Scope

獨立審查source-pinned compatibility patch、Hermes user plugin、SQLite queue open semantics、artifact/prerequisite/wheel verifier、tests、production preflight evidence與approval/rollback boundary。審查不修改repository或production。

## First-Round Findings

### High — production prerequisite verifier只比dirty paths

- 風險：相同paths但不同內容可能通過preflight。
- 修復：`verify_artifacts.py`現在比對integration、variant、manifest digest、實際patch bytes，並鏈接`integrations/hermes/verify_patch.py --expect applied`；回傳variant/digest/state也需一致。
- Regression：`test_production_prerequisite_rejects_same_path_with_changed_patch_bytes`。
- 結論：closed。

### High — plugin registration仍可能執行queue schema initialization

- 風險：read-only schema validation後呼叫一般constructor，仍會執行`_initialize()`。
- 修復：新增`SQLiteHermesDeliveryQueue.open_existing()`；不建立parent、不呼叫`_initialize()`。Plugin改用此入口。
- Regression：legacy schema拒絕後DB bytes/schema不變；valid DB註冊時monkeypatch `_initialize()`為failure仍可成功。
- 結論：closed。

### Medium — wheel不在統一manifest/verifier

- 修復：manifest新增filename、SHA-256、`SOURCE_DATE_EPOCH`；verifier新增`--release-wheel`實體digest gate。
- 結論：closed。

### Medium — canonical runner與production preflight職責

- 判定：canonical runner只負責isolated exact-source patched Hermes；production prerequisite/content/drift由`--check-production-drift`負責。此職責分離已由RUNBOOK固定，不是open defect。
- 結論：closed by design clarification。

## Final Independent Review

- High：0
- Medium：0
- Low：2，non-blocking

### Low 1 — `open_existing()`名稱不代表自行驗完整schema

Plugin在呼叫前已做完整schema/owner/mode/integrity驗證，因此本Stage安全路徑正確。未來若新增caller，需避免將`open_existing()`誤解為schema validator。

### Low 2 — production dirty-path exact equality偏嚴格

任何額外live checkout drift都會fail closed。這是刻意的production治理策略，可能增加操作摩擦但不降低安全性。

## Verified Gates

- Focused plugin/consumer/dispatcher/verifier：`29 passed`
- Canonical repository suite：`100 passed`
- Source-pinned Hermes compatibility runner：`3 passed`
- Ruff format/lint：PASS
- Compileall：PASS
- Documentation governance：PASS
- Live verifier：context patch`applicable`，existing prerequisite patch內容與state`applied`
- Isolated verifier：context patch`applied`
- Reproducible wheel：兩次byte-identical，clean venv plugin smoke PASS，manifest verifier PASS

## Verdict

**Repository production-artifact readiness: ACCEPT.**

**Production deployment authorization: WITHHELD.**

本review不授權套production patch、安裝plugin、建立delivery DB、claim既有pending item、修改systemd/config、restart service或執行platform canary。所有production mutation仍受`RUNBOOK-002`的獨立書面approval gate約束。
