---
id: PLAN-001
title: Runtime-neutral foundation 第一個工程增量
type: plan
status: active
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-000
related_adrs:
  - ADR-0001
  - ADR-0002
related_evidence:
  - EVID-001
---

# PLAN-001：Runtime-neutral foundation 第一個工程增量

## Objective

把現有 Hermes-only planning architecture 轉為 runtime-neutral 設計，建立最小、可測、無 vendor dependency 的 Agent Runtime SPI，同時落實 repository-native 文件治理。

## Scope

### In scope

- 文件治理、追溯、狀態與 evidence baseline。
- 更新 README、Architecture、Project Plan、Security、Threat Model、MCP 與 compatibility 文件。
- 定義 runtime descriptor、capabilities、execution task/handle/status。
- 明確區分 worker lifecycle 與 verification lifecycle。
- 定義 Agent Runtime protocol 與 registry。
- 建立 fake runtime contract tests。
- 建立文件治理檢查器。

### Out of scope

- Hermes、Claude Code、Codex、AGY 或 Grok Build 真實 adapter。
- AgentMemoryOS 真實網路整合。
- Durable persistence、queue 或 event bus。
- Production execution 與 credentials。
- Runtime Router 的成本/品質模型。

## Work Items

1. `DOC-01`：建立 governance、traceability、status、goal、stage、plan。
2. `DOC-02`：建立 ADR-0001 runtime-neutral architecture。
3. `DOC-03`：建立 ADR-0002 documentation governance。
4. `DOC-04`：同步既有架構、安全與 compatibility 文件。
5. `TST-01`：先建立 registry 與 contract 的失敗測試。
6. `IMP-01`：實作 immutable runtime models 與 errors。
7. `IMP-02`：實作 AgentRuntime protocol 與 RuntimeRegistry。
8. `IMP-03`：實作只供測試的 FakeRuntime。
9. `TST-02`：執行 focused/full tests 與文件檢查。
10. `EVID-01`：記錄可重現驗證結果。
11. `REV-01`：獨立審查 diff、風險與治理一致性。

## Deliverables

- `docs/GOVERNANCE.md`
- `docs/TRACEABILITY.md`
- `docs/PROJECT_STATUS.md`
- `docs/goals/GOAL-001-*.md`
- `docs/stages/STAGE-000-*.md`
- `docs/plans/PLAN-001-*.md`
- `docs/adr/0001-runtime-neutral-agent-runtime.md`
- `docs/adr/0002-repository-native-documentation-governance.md`
- `src/bastet_engramflow/runtimes/`
- `tests/`
- `scripts/check_docs.py`
- `docs/evidence/EVID-001-*.md`
- `docs/reviews/REVIEW-001-*.md`

## Acceptance Criteria

1. 所有核心 runtime models 與 registry tests 通過。
2. Duplicate runtime ID、missing runtime、capability mismatch 與 invalid handle 有明確錯誤。
3. Worker completion 不會自動產生 verified 狀態。
4. Runtime registry 以 capability detection 查詢，不以版本字串分支。
5. Core package 不含 Hermes、Claude、Codex、AGY、Grok vendor imports。
6. 文件治理檢查器通過且可偵測 broken governance reference。
7. `PROJECT_STATUS.md`、Goal、Stage、Plan、ADR 與 evidence 互相一致。
8. Compatibility matrix 不把未經 E2E 的 runtime 標記為 Supported。
9. 獨立 review 沒有未處理的 high-severity finding。

## Verification

- `python -m unittest discover -s tests -v`
- `python scripts/check_docs.py`
- `python -m compileall -q src scripts tests`
- Git diff、status 與 secret/path audit。

## Risks and Mitigations

- **SPI 過度設計**：v1 僅保留 submit/status/cancel、capabilities、registry。
- **Vendor leakage**：core tests 搜尋 vendor imports/identifiers。
- **假完成**：execution 與 verification 分軸建模。
- **文件漂移**：status 與引用由檢查器驗證。
- **跨 Agent workspace 衝突**：後續 adapter 必須使用 sandbox/worktree policy。

## Rollback

本階段沒有 production side effect。可透過回退 branch commit 恢復文件規劃狀態；不得刪除已發布的 ADR/evidence，而應標記 superseded/rejected。
