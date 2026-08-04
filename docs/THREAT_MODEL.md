# Threat Model

- 狀態：Draft
- 範圍：Bastet-EngramFlow planning architecture
- 方法：以 assets、trust boundaries、threats、controls 與 verification cases 維護

## 1. Assets

- AgentMemoryOS 記憶內容、ACL、provenance 與 resonance score
- ActionProposal、approval、policy 與 audit lineage
- Agent Runtime execution identity、adapter/runtime version、tool capability、workspace 與 task state
- credentials、tokens、keys 與 external service permissions
- verification artifacts 與 feedback records
- project/user isolation boundary

## 2. Trust boundaries

1. 外部事件／內容 → Trigger Gateway
2. AgentMemoryOS → EngramFlow adapter
3. LLM-generated association → deterministic policy
4. Policy Gateway → Runtime Router → selected Agent Runtime
5. Worker self-report → independent verifier
6. EngramFlow feedback → AgentMemoryOS
7. Runtime → external systems

所有跨 boundary 資料必須經 schema validation、scope/ACL 檢查與 sanitized logging。

## 3. Threats and controls

### Prompt injection / instruction smuggling

- 威脅：外部資料或 memory text 誘導模型繞過 policy。
- 控制：untrusted labeling、deterministic policy、capability allowlist、parameter validation。
- 測試：惡意 content 不得擴大 toolsets、risk tier 或 approval scope。

### Memory poisoning

- 威脅：錯誤／惡意記憶被高權重共鳴並觸發行動。
- 控制：provenance、confidence、ACL、correction history、多證據要求。
- 測試：低可信單一記憶不得觸發 high/critical action。

### Cross-project data leakage

- 威脅：proposal 或 evidence 夾帶其他 project/user 記憶。
- 控制：query-time ACL、proposal validation、project-scoped identity、redaction。
- 測試：跨 scope fixture 必須被拒絕且 audit 不保存原文。

### Approval tamper / replay

- 威脅：修改 proposal 後沿用舊批准，或重放過期批准。
- 控制：approval 綁定 proposal digest、capability、target、identity、expiry。
- 測試：任何綁定欄位改變都使 approval 失效。

### Duplicate or unintended side effects

- 威脅：retry、network timeout 或重複 trigger 造成重複寫入。
- 控制：idempotency key、dedup window、single active run、external read-back。
- 測試：相同 key 的並行與 retry 只能產生一個邏輯副作用。

### Privilege escalation

- 威脅：低風險 proposal 呼叫未批准的高權限工具。
- 控制：action-class identity、tool allowlist、effective capability intersection。
- 測試：requested capability 超出 policy/approval 時 fail closed。

### False completion

- 威脅：worker 或 MCP response 宣告成功但外部狀態未改變。
- 控制：independent verifier、artifact hash、API/DB/service/Git read-back。
- 測試：self-report success + failed read-back 必須為 verification failure。

### Secret disclosure

- 威脅：credential 出現在 Git、prompt、memory、logs 或 evidence。
- 控制：secret manager、redaction、reference/digest、secret scanning。
- 測試：canary secret 不得出現在任何一般 telemetry 或 artifact。

### Denial of service / cost exhaustion

- 威脅：resonance storm、recursive trigger 或昂貴 API loop。
- 控制：rate limit、cooldown、budget、depth limit、kill switch。
- 測試：burst 與 feedback loop 被限流且不繞過 audit。

### Cross-runtime workspace corruption

- 威脅：一個 Agent timeout/失敗後，另一個 Agent 在未驗證的 dirty workspace 繼續修改，造成覆蓋、重複副作用或來源不明的 artifact。
- 控制：per-run worktree/sandbox、base commit binding、artifact manifest、fallback 前 read-back、禁止盲目共用 vendor session。
- 測試：workspace-write fallback 必須取得乾淨隔離 workspace；dirty state 未被明確採納時 fail closed。

### Runtime capability spoofing

- 威脅：adapter 或 runtime 宣稱支援 cancel、sandbox、tool restriction 等能力，但實際無法強制。
- 控制：pinned version、capability contract tests、effective permission intersection、Experimental/Supported promotion gate。
- 測試：每個 Supported capability 必須有真實 probe；probe 失敗時 runtime 不得被 Router 選用於要求該能力的任務。

## 4. High-risk default policy

Production writes、deletion、payment、permission changes、credential operations、public posting 與 service-wide restart 預設要求人工批准；critical 類別預設禁止自動執行。

## 5. Residual risks / TBD

- AgentMemoryOS 的實際 ACL 與 provenance contract 尚未取得。
- 各 Agent Runtime integration identity、workspace 與 sandbox boundary 尚未逐一選定。
- MCP 版本／transport／auth baseline 尚未 ADR。
- retention、privacy jurisdiction 與 incident owner 尚未定案。

## 6. Release evidence

每個 release 必須連結：

- threat-model diff
- security test results
- secret/dependency scan
- policy denial tests
- approval replay/tamper tests
- verifier independence evidence
- kill-switch rehearsal result
