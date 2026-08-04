# Contributing to Bastet-EngramFlow

## 原則

- 先釐清 contract、風險與驗收，再實作。
- 認知、政策、執行、驗證維持清楚邊界。
- 行為變更採 RED → GREEN → REFACTOR。
- 不提交 secret、private key、token、production payload 或個資。
- 不以 Agent／worker 自行宣告成功取代測試或 read-back。

## 建議流程

1. 建立 issue，描述問題、作用域、風險與 acceptance criteria。
2. 若涉及架構／protocol／security，先新增 ADR。
3. 建立 focused branch。
4. 先寫或更新測試。
5. 實作最小變更。
6. 執行 unit、contract 與相關 integration tests。
7. 檢查 diff、secret scan、dependency 與文件。
8. 建立 PR，附上真實驗證輸出。

所有變更必須先確認對應 `GOAL-*`、`STAGE-*` 與 `PLAN-*`；詳細規則見 `docs/GOVERNANCE.md` 與 `docs/TRACEABILITY.md`。若目前 active plan 不涵蓋該工作，應先更新或新增 plan，不可讓實作脫離治理鏈。

## Commit convention

```text
feat: add action proposal schema
fix: enforce approval digest binding
docs: define MCP compatibility baseline
test: cover duplicate execution prevention
chore: configure CI checks
```

## Pull request checklist

- [ ] Scope 與 acceptance criteria 清楚
- [ ] Tests 先失敗後通過（適用時）
- [ ] Risk tier / ACL / idempotency 已處理
- [ ] 不含 secrets 或本機絕對 credential paths
- [ ] Contract/schema 版本已更新
- [ ] `docs/COMPATIBILITY_MATRIX.md` 已更新
- [ ] `docs/PROJECT_STATUS.md` 與相關 Goal/Stage/Plan 已更新
- [ ] ADR/Evidence/Review 已依治理規則建立或更新
- [ ] Verification evidence 已附上
- [ ] Rollback / disable path 已說明

## Documentation states

請明確區分：

- **remembered**：存於記憶系統
- **materialized**：已寫入檔案
- **versioned**：已 commit
- **published**：已 push 並從 remote 驗證
