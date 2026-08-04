---
id: STAGE-000
title: Runtime-neutral foundation
type: stage
status: active
owner: project-maintainers
created: 2026-08-05
updated: 2026-08-05
stage_order: 0
related_goals:
  - GOAL-001
related_plans:
  - PLAN-001
---

# STAGE-000：Runtime-neutral foundation

## Purpose

建立可持續演進的治理、contract 與測試基線，先證明 runtime-neutral narrow waist，再開始任何 vendor adapter。

## Entry Criteria

- Repository 與 remote 已確認。
- 既有 architecture、project plan、security 與 compatibility 文件已盤點。
- Owner 同意從 Hermes-only 擴展為多 Agent Runtime。
- Owner 要求嚴格文件治理與全程可追溯。

## Deliverables

1. Governance、traceability 與 project status 基線。
2. Runtime-neutral 架構與專案計畫。
3. Agent Runtime SPI、capability model、registry 與錯誤模型。
4. Focused unit/contract tests。
5. Compatibility matrix 初始 runtime rows。
6. Evidence 與獨立 review。

## Exit Criteria

- `PLAN-001` 所有 acceptance criteria 有 evidence。
- Runtime Core 不依賴任何 vendor SDK。
- Registry 與 lifecycle contract tests 通過。
- 文件治理檢查通過。
- Architecture、project plan、security、threat model 與 compatibility matrix 一致。
- 變更已 versioned；若發布，remote read-back 已驗證。

## Dependencies

- Python 3.11+。
- AgentMemoryOS 真實 contract 後續 pin。
- 各 runtime 官方 SDK/CLI/protocol 版本於 adapter stage 個別 pin。

## Risks

- 過早加入 vendor 細節破壞核心抽象。
- 過度設計 lifecycle 阻礙第一個 adapter。
- 治理文件與實際 Git 狀態不同步。
