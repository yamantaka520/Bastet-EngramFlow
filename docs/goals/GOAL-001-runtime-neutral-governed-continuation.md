---
id: GOAL-001
title: Runtime-neutral 受治理主動專案延續
type: goal
status: active
owner: project-maintainers
created: 2026-08-05
updated: 2026-08-05
related_stages:
  - STAGE-000
---

# GOAL-001：Runtime-neutral 受治理主動專案延續

## Goal Statement

讓 AgentMemoryOS 的記憶分級與記憶共鳴，能透過 Bastet-EngramFlow 安全驅動多種主流 Agent Runtime，持續提出、執行與驗證專案下一步，而不綁定單一 Agent 產品。

目標 runtime 包含 Hermes Agent、Claude Code、OpenAI Codex、AGY/Antigravity CLI、Grok Build，並允許後續透過薄 adapter 擴充。

## Success Criteria

1. EngramFlow Core 不匯入 vendor SDK 或洩漏 vendor-specific schema。
2. Runtime 透過版本化 SPI 註冊並宣告實際 capabilities。
3. 同一個 bounded execution task 可由至少三個通過 contract/E2E 的 runtime adapter 接收。
4. 任務延伸必須經 proposal、policy、budget、idempotency 與 depth gate。
5. Worker completion 與 independent verification 分離。
6. 跨 Agent handoff 使用可攜式 context/artifact contract，不假設 session 可互換。
7. 所有 Supported 聲明具版本、測試與 evidence。
8. 專案目標、階段、計畫、決策、證據與狀態可由 repository 重建。

## Non-goals

- 不建立不受控的無限自治迴圈。
- 不統一或重寫各 vendor 的 conversation loop。
- 不把 MCP、ACP 或純文字 CLI 當成所有 lifecycle 問題的單一解答。
- 不以 Agent 自述作為完成證據。
- 第一階段不提供 production write、付款、刪除或權限變更的無人批准自動化。

## Traceability

- Stage：`STAGE-000`
- Active plan：`PLAN-001`
- Architecture decision：ADR-0001、ADR-0002
