# Compatibility Matrix

此文件是 Bastet-EngramFlow 的唯一相容性矩陣來源。只有具有真實 contract/integration/E2E 證據的組合可以標記 Supported。

## 狀態定義

- **TBD**：尚未 pin 或測試。
- **Experimental**：已有初步測試，不構成 release guarantee。
- **Supported**：已通過 release gate 與必要 contract/E2E tests。
- **Unsupported**：已知不相容或明確不支援。

## Runtime matrix

| Component | Version / Commit | Interface | Status | Evidence |
|---|---|---|---|---|
| AgentMemoryOS | TBD | native adapter | TBD | source-first assessment pending |
| EngramFlow Runtime SPI | `0.1.0-dev` | Python protocol/registry | Experimental | PLAN-001 contract tests pending |
| Hermes Agent | `1072c0725115e9be0491ca4cb0d965b9f5f59874` | structured cron result + proposed `post_cron_job` hook | Experimental | STAGE-002 contracts; STAGE-003 pinned integration active |
| Hermes Agent latest tag | TBD | compatibility lane | TBD | CI pending |
| Hermes Agent main | moving | early-warning only | Experimental | non-release-gating lane pending |
| Claude Code | TBD pinned version | Agent SDK/headless/MCP/hooks candidate | TBD | source-first assessment pending |
| OpenAI Codex | TBD pinned version | Codex SDK/MCP server candidate | TBD | source-first assessment pending |
| AGY / Antigravity CLI | TBD pinned version | structured CLI/MCP candidate | TBD | machine-readable lifecycle assessment pending |
| Grok Build | TBD pinned version | streaming JSON CLI/Responses API/MCP candidate | TBD | source-first assessment pending |

## Runtime capability matrix

本表是 discovery backlog，不是支援承諾。`?` 表示必須以 pinned version 真實測試。

| Runtime | Structured lifecycle | Cancel | Resume | Sandbox/workspace | MCP | Preferred integration | Status |
|---|---|---|---|---|---|---|---|
| Hermes Agent | ? | ? | ? | ? | client/server candidate | native task/plugin/MCP | TBD |
| Claude Code | ? | ? | ? | ? | client candidate | Agent SDK | TBD |
| OpenAI Codex | ? | ? | ? | ? | client/server candidate | Codex SDK | TBD |
| AGY | ? | ? | ? | ? | client candidate | structured CLI | TBD |
| Grok Build | ? | ? | ? | ? | client candidate | streaming JSON CLI/API | TBD |

## MCP matrix

| Component | Implementation Version | Official Protocol Version | Transport | Auth | Status | Evidence |
|---|---|---|---|---|---|---|
| AgentMemoryOS MCP | `>=2.0.0`（需求，定義待確認） | date version TBD | TBD | TBD | TBD | owner decision + E2E pending |
| EngramFlow MCP adapter | semantic version TBD | date version TBD | TBD | TBD | TBD | contract tests pending |
| Hermes MCP client | pinned Hermes version TBD | date version TBD | stdio | local | TBD | contract test pending |
| Hermes MCP client | pinned Hermes version TBD | date version TBD | HTTP | OAuth/bearer/mTLS TBD | TBD | contract test pending |
| Claude Code MCP client | pinned version TBD | date version TBD | stdio/HTTP TBD | TBD | TBD | contract test pending |
| Codex MCP client | pinned version TBD | date version TBD | stdio/HTTP TBD | TBD | TBD | contract test pending |
| Grok Build MCP client | pinned version TBD | date version TBD | stdio/HTTP TBD | TBD | TBD | contract test pending |

## Language / dependency matrix

| Item | Range | Status | Evidence |
|---|---|---|---|
| Python | proposed `>=3.11` | TBD | ADR pending |
| AgentMemoryOS SDK | TBD with explicit upper bound | TBD | clean-env resolution pending |
| Runtime adapter dependencies | each pinned/compatible range TBD | TBD | per-adapter clean-env + contract tests pending |

## Promotion rule

將任何列從 TBD/Experimental 升級為 Supported 前，必須記錄：

1. exact version/tag/commit；
2. clean environment dependency resolution；
3. focused contract tests；
4. required integration/E2E tests；
5. known limitations；
6. evidence URL 或 artifact reference。

`main`/nightly 僅作 drift early warning，不會自動成為 production support promise。
