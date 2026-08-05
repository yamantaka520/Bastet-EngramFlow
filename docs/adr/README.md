# Architecture Decision Records

ADR 用來記錄 Bastet-EngramFlow 的重要、長期且具取捨的技術決策。規劃文件中的 TBD 不代表已定案；只有 Accepted ADR 才是正式架構決策。

## 狀態

- Proposed
- Accepted
- Superseded
- Deprecated
- Rejected

## 命名

```text
NNNN-short-kebab-case-title.md
```

例如：`0001-runtime-language.md`。

## 流程

1. 複製 [template.md](template.md)。
2. 填寫 context、options、decision、consequences 與 verification。
3. PR review 後將狀態改為 Accepted 或 Rejected。
4. 後續決策不得覆寫舊 ADR；建立新 ADR 並標記 supersedes/superseded by。
5. 若影響版本相容性，同步更新 `docs/COMPATIBILITY_MATRIX.md`。

## Phase 0 待建立 ADR

1. Runtime language and package strategy
2. Persistence and event model
3. AgentMemoryOS adapter contract
4. Agent Runtime SPI、routing 與 adapter seam（ADR-0001 Accepted）
5. MCP compatibility baseline
6. Risk tiers and approval model
7. Verification evidence model
8. Repository-native documentation governance（ADR-0002 Accepted）
