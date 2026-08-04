# Bastet-EngramFlow

**Memory Resonance Runtime for Autonomous Agents**
以記憶共鳴驅動自主 Agent 關聯、推理、提案、執行與驗證的開源架構。

> 專案狀態：Planning / Draft `0.1`

## 願景

Bastet-EngramFlow 將自研 **AgentMemoryOS** 與 **Hermes Agent** 整合，把被動的「查詢記憶」提升為可治理的主動式流程：

```text
Memory → Resonance → Proposal → Policy → Execution → Verification → Feedback
```

系統根據目標、事件及記憶關聯產生候選行動，但不讓「想到」直接等於「執行」。所有行動須經風險、去重、冷卻、預算、授權與驗證機制治理。

## 核心原則

- **記憶有證據**：提案必須攜帶來源、關聯理由與可信度。
- **認知與執行分離**：AgentMemoryOS 負責記憶／共鳴；Hermes 負責工具與任務執行。
- **Policy before Action**：高風險、不可逆或對外操作不得自動放行。
- **Completion requires Evidence**：worker 回報完成不等於驗證完成。
- **Adapter over Fork**：優先使用 Hermes plugin、MCP、hook 與 task API，避免深度 fork。
- **Shadow-first**：先觀察提案品質，再逐類開放自治權限。

## 文件索引

- [完整專案計畫](docs/PROJECT_PLAN.md)
- [系統架構](docs/ARCHITECTURE.md)
- [MCP 相容性策略](docs/MCP_COMPATIBILITY.md)
- [相容性矩陣](docs/COMPATIBILITY_MATRIX.md)
- [安全與治理](docs/SECURITY_AND_GOVERNANCE.md)
- [威脅模型](docs/THREAT_MODEL.md)
- [Architecture Decision Records](docs/adr/README.md)
- [貢獻指南](CONTRIBUTING.md)

## 第一階段交付目標

1. 定義 `MemorySignal`、`ActionProposal`、`PolicyDecision`、`ExecutionRun`、`VerificationResult` 與 `FeedbackRecord` 契約。
2. 建立 AgentMemoryOS adapter 與 Hermes adapter。
3. 實作 shadow mode：只產生與記錄提案，不執行副作用。
4. 加入 deduplication、cooldown、budget、risk tier 與 approval gate。
5. 建立端到端 contract tests 與稽核軌跡。

> 「MCP 2.0+」是需求原文；官方 Model Context Protocol 使用日期版號。實際版本軸與 baseline 必須依 [MCP 相容性策略](docs/MCP_COMPATIBILITY.md) 決議，不能直接把兩者視為同一版本。

## 快速狀態

目前 repository 已建立主要規劃文件與治理骨架；尚未進入 production implementation。技術選型與里程碑請以 `docs/PROJECT_PLAN.md` 為準，未決策項目仍須透過 ADR 定案。

## License

Apache License 2.0。詳見 [LICENSE](LICENSE)。
