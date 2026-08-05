# ADR-0001：Runtime-neutral Core 與薄 Agent Runtime Adapters

- Status：Accepted
- Date：2026-08-05
- Decision owners：Project maintainers
- Related：GOAL-001、STAGE-000、PLAN-001

## Context

Bastet-EngramFlow 原始規劃將 AgentMemoryOS 的記憶共鳴直接交由 Hermes Agent 執行。專案現在要求同時支援 Hermes Agent、Claude Code、OpenAI Codex、AGY/Antigravity CLI、Grok Build 與後續主流 Agent，同時保留政策治理、獨立驗證與可追溯性。

不同 runtime 對 SDK、MCP、ACP、CLI、session、sandbox、cancel、artifact 與 structured events 的支援不一致。若 Core 直接依賴任一 vendor schema，將造成深度耦合與相容性漂移。

## Decision Drivers

- Core 必須可長期獨立於 Agent vendor 演進。
- 不得把 MCP 誤用成完整 durable execution lifecycle。
- Runtime 必須誠實宣告 capabilities，不得模擬不具備的能力。
- Worker completion 與 independent verification 必須分離。
- 跨 Agent handoff 不能假設原生 session 可攜。
- Vendor 更新只應影響對應 adapter 與 compatibility lane。

## Options Considered

### A. Hermes-only 深度整合

優點：初期最快。缺點：不符合多 runtime 目標，Core 會承擔 Hermes upstream drift。

### B. 所有 Agent 統一走純文字 CLI

優點：介面表面一致。缺點：缺少可靠 lifecycle、tool events、cancel、usage、artifact 與 structured error，無法支撐 Supported 等級。

### C. Runtime-neutral SPI + thin adapters

Core 定義 execution task、handle、status、capabilities、registry 與 verification contract；每個 adapter 選用該 vendor 最穩定的 native SDK/API、MCP/ACP 或 structured CLI。

## Decision

採用 Option C。

1. Core 提供版本化 `AgentRuntime` SPI，不匯入 vendor SDK。
2. Runtime adapter 優先順序為 native SDK/API，其次正式 protocol，再其次 structured CLI；純文字 CLI 僅允許 Experimental。
3. Registry 依 capability discovery 選擇 runtime，不依版本字串推測功能。
4. Execution state 表示 worker lifecycle；verification state 由獨立 verifier 管理。
5. 跨 Agent continuation 使用版本化 Agent Context Bundle 與 artifact references，不交換 vendor session store。
6. MCP 定位為工具／資料／memory context plane；ACP 定位為可選的 client↔agent session plane；durable task control 由 adapter contract 負責。
7. 所有 runtime 在通過真實 contract/E2E 前維持 TBD 或 Experimental。

## Consequences

### Positive

- Core 可支援多 Agent 而不形成永久 fork。
- Vendor-specific drift 可由 adapter contract tests 隔離。
- Policy、audit 與 verifier 對所有 Agent 一致。
- Runtime Router 可依 capabilities、cost、trust 與 workspace policy 選擇 Agent。

### Negative

- 需要維護多個 adapter 與 compatibility matrix。
- 能力最低公分母不足以表達所有 vendor 特性，需保留 namespaced metadata。
- 不能承諾任意 Agent 間直接 resume 同一 session。
- CLI-only runtime 的支援等級可能長期低於 native SDK runtime。

## Verification

- Core source 不得有 vendor SDK import。
- Fake runtime 通過 SPI contract tests。
- Registry 能依 capabilities 篩選。
- Worker success 不會自動變成 verified。
- 每個正式 adapter 需獨立通過 submit/status/cancel/artifact/tool-call/E2E 測試。

## Rollback / Supersession

若實作證明單一 SPI 無法維持，必須新增 ADR 描述拆分方式並 supersede 本 ADR；不得直接把 vendor schema滲入 Core。
