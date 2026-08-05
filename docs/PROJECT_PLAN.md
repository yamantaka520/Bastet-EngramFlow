# Bastet-EngramFlow 專案計畫

- 文件版本：`0.10.0`
- 更新時間：2026-08-05 18:21 CST（UTC+8）
- 專案狀態：STAGE-007 accepted / fail-closed reconciliation dispatcher readiness
- Repository：`yamantaka520/Bastet-EngramFlow`
- 授權：Apache-2.0

## 1. 專案摘要

Bastet-EngramFlow 是 AgentMemoryOS 與可插拔 Agent Runtime 之間的主動式聯想、治理與驗證層。它將分級記憶與「記憶共鳴」轉換成帶證據的行動提案，再由可稽核的政策層決定是否拒絕、等待批准、進入 shadow mode，或交由 Hermes Agent、Claude Code、OpenAI Codex、AGY/Antigravity CLI、Grok Build 等 runtime 執行。

核心流程：

```text
Trigger
  ↓
Memory retrieval + resonance
  ↓
Candidate associations
  ↓
Structured ActionProposal
  ↓
Policy / risk / dedup / cooldown / budget / approval
  ↓
Runtime Router → selected Agent Runtime
  ↓
Independent verification
  ↓
Outcome feedback to AgentMemoryOS
```

## 2. 問題定義

一般 Agent 記憶多半是被動檢索：只有收到問題時才取回上下文。這會造成：

- 已知的重要關聯無法在適當時間主動浮現。
- 記憶、推理與任務執行缺乏統一、可追溯的因果鏈。
- 模型可能把「聯想到某件事」直接轉成副作用，缺乏治理。
- worker 自行宣告成功，沒有獨立證據驗證。
- 記憶結果若未回饋成結構化成效，系統難以改善觸發品質。
- 隔離的排程 agent run 雖能獨立執行，卻無法把問題與結果主動帶回原 conversation 討論或形成受治理的修復提案。

本專案要解決的問題不是「讓 Agent 做更多事」，而是「讓 Agent 在正確時間，基於可解釋記憶，提出正確且可治理的行動」。

## 3. 願景與目標

### 3.1 願景

建立一個可插拔、可驗證、可逐步提升自治程度的 Memory Resonance Runtime，使 AgentMemoryOS 的記憶能力能安全地驅動多種 Agent Runtime 的任務執行能力。

### 3.2 MVP 目標

- 接收事件、排程、目標變化或對話中的 trigger。
- 從 AgentMemoryOS 取得分級記憶及 resonance 結果。
- 產生符合 schema 的 `ActionProposal`。
- 執行政策判定：風險、重複、冷卻、預算、授權與作用域。
- 在 shadow mode 完整記錄「若開放自動化會做什麼」。
- 將低風險、允許的工作依 capability 與 policy 提交給適合的 Agent Runtime。
- 由獨立 verifier 檢查 artifact、exit status 或 read-back state。
- 將結果與品質指標回寫 AgentMemoryOS。
- 將 scheduled run 的 structured result/finding 回流 conversation inbox，並在安全 gate 下建立 remediation proposal。

### 3.3 非目標

- 不重寫任何 vendor 的 conversation loop 或完整 tool runtime。
- 不讓 AgentMemoryOS 直接執行 production 副作用。
- 不以模型自評作為唯一完成證據。
- MVP 不開放付款、刪除、權限變更、production write 或公開發布的無人批准自動化。
- 不在第一階段建立大型通用 workflow engine；優先重用各 runtime 已存在的 durable task、SDK、MCP/ACP、hook 與 structured CLI 能力。

## 4. 成功指標

### 4.1 Shadow mode

- Proposal precision：人工標記為「有用」的比例。
- False-trigger rate：不應觸發卻觸發的比例。
- Duplicate rate：相同意圖重複提案比例。
- Evidence coverage：具有效 memory evidence 的提案比例，目標 100%。
- Explainability coverage：具 `why_now` 與 acceptance criteria 的比例，目標 100%。

### 4.2 執行階段

- Verified success rate：經獨立 verifier 通過的執行比例。
- Worker/Verifier disagreement：worker 宣告完成但 verifier 失敗的比例。
- Approval correctness：高風險操作未經批准即執行必須為 0。
- Idempotency violations：同一 idempotency key 產生重複副作用必須為 0。
- Mean time to verified outcome。

量化門檻將在取得 shadow mode 基線後，透過 ADR 固定，避免在沒有資料前虛設精準數字。

## 5. 使用情境

### 5.1 主動提醒與研究

當事件與歷史目標／未完成決策產生高關聯時，系統提出研究、摘要或提醒建議；預設可自動執行 read-only 資料蒐集，但對外發送仍由 policy 控制。

### 5.2 健康檢查與異常關聯

服務事件與歷史故障記憶共鳴後，產生診斷提案。第一階段只允許 read-only checks；重啟、修改設定或修復 production 需批准。

### 5.3 文件與報告生成

當排程、資料更新或專案里程碑符合條件時，提出產生草稿／報告的行動。artifact 必須能被 read-back 驗證。

### 5.4 任務延續

從未完成目標、blocked reason 與新事件判斷工作是否可恢復，並建立帶上下文與驗收條件的 vendor-neutral execution task，再交由 Runtime Router 選擇 Agent。

### 5.5 排程結果回流與主動修復

排程 agent 維持獨立 session/process；完成、失敗或 blocked 時提交 structured run envelope。Reconciler 將結果投遞到原 conversation inbox，讓使用者與 agent 可納入後續討論；retryable 問題形成 remediation proposal，但 external side effect、critical、non-idempotent 或 depth-exhausted 一律等待批准。

## 6. 功能需求

### FR-01 Trigger ingestion

支援至少：

- 使用者明示請求
- webhook/event
- cron/schedule
- Agent Runtime lifecycle event
- AgentMemoryOS resonance threshold event

所有 trigger 必須具有來源、時間、作用域、correlation ID 與 payload digest。

### FR-02 Memory retrieval and resonance

- 支援 AgentMemoryOS 記憶分級。
- 回傳 memory ID、類型、權限、時間、來源與 relevance/resonance score。
- 不得把超出 project/user ACL 的記憶帶入提案。
- 原始敏感記憶應優先以 reference 取代全文複製。

### FR-03 Proposal generation

每個提案至少包含：

```yaml
proposal_id: string
schema_version: string
created_at: datetime
trigger_id: string
why_now: string
memory_evidence:
  - memory_id: string
    relation: string
    score: number
expected_outcome: string
acceptance_criteria: [string]
confidence: number
risk_tier: low|medium|high|critical
idempotency_key: string
required_approval: none|user|operator|admin
requested_capabilities: [string]
origin_version: string
```

提案只描述意圖與驗收，不直接聲稱執行完成。

### FR-04 Policy engine

政策至少處理：

- ACL / project boundary
- capability allowlist
- risk tier
- approval requirement
- deduplication
- cooldown
- daily/per-run budget
- rate limit
- idempotency
- data classification
- environment（dev/staging/production）

政策輸出必須包含 machine-readable decision code 與 human-readable reason。

### FR-05 Agent Runtime SPI、routing 與 execution adapters

- Core 定義 vendor-neutral runtime descriptor、capabilities、task、handle、status 與 error contract。
- 優先透過 native SDK/API，其次正式 MCP/ACP seam，再其次 structured CLI 整合；純文字 CLI 僅能作 Experimental bridge。
- 避免直接寫入任何 runtime 的內部 database 或 session store。
- 將 proposal 轉成 bounded task，攜帶 acceptance criteria、timeout、workspace、budget 與允許 capabilities。
- 儲存 adapter/runtime version 與 task/session/process/run ID，支援能力可用時的 cancel、timeout 與 retry policy。
- Runtime Router 依 capability、health、policy、cost 與 workspace isolation 選擇 runtime；不可用版本字串猜測能力。
- `worker_reported_done` 不得直接轉成 `verified`。

### FR-06 Independent verification

依工作類型至少驗證其中一項：

- command exit status
- artifact existence、hash、格式或內容
- API read-back
- database read-only query
- service health/readiness
- remote Git commit/ref
- human approval/inspection

Verifier 不得只重述 worker 的文字結果。

### FR-07 Feedback

回寫：

- policy decision
- execution outcome
- verification result
- user accept/reject/correction
- false trigger / duplicate / timeout 類型
- association reinforcement 或 suppression signal

原始事件不可因 feedback 被覆蓋；使用 append-only audit model。

### FR-08 MCP compatibility

- 專案要求的「MCP 2.0+」必須有明確 compatibility contract。
- MCP adapter 需支援 Hermes 作為 MCP client 的整合方式。
- 支援 local stdio 與 remote HTTP 的目標由 phase 決定；MVP 至少完成一條 transport 的 end-to-end contract test。
- 工具 discovery、schema validation、timeout、error mapping、auth 與 capability filtering 必須測試。
- 詳見 [MCP_COMPATIBILITY.md](MCP_COMPATIBILITY.md)。

### FR-09 Scheduled execution reconciliation

- Scheduled run 以 `ScheduledRunEnvelope` 回報 schedule/run identity、origin conversation、outcome、findings、artifacts 與 continuation depth。
- Reconciler 產生 `ConversationContextEvent`，只透過 idempotent inbox port 回流，不直接修改 vendor session store。
- Finding 可形成帶 `why_now`、lineage、idempotency 與 acceptance criteria 的 `RemediationProposal`。
- Core 只判斷 `auto_eligible` 或 `approval_required`；不直接聲稱修復已執行或 verified。
- `(schedule_id, run_id)`、event ID 與 proposal ID 必須穩定；reference coordinator 提供 process-local 去重。
- Sink failure 時不得 local-commit run key；重試依賴 sink idempotency 避免邏輯重複。Production 跨重啟／多實例保證需 durable ledger/outbox。

## 7. 非功能需求

### 7.1 Security

- least privilege 與 capability-based access。
- secrets 僅從安全的 runtime secret source 載入，不進 Git、memory evidence 或 log。
- 所有副作用需可追蹤到 trigger、proposal、policy decision、execution 與 verification。
- prompt injection 不得繞過 policy engine。

### 7.2 Reliability

- event 與 proposal 處理需可重試且具 idempotency。
- timeout、partial failure、worker crash、network partition 必須可辨識。
- audit record 寫入失敗時，禁止進行高風險操作。

### 7.3 Portability

- 避免 hard-coded home path、profile path 或單一主機配置。
- 使用 environment variables 與設定檔。
- 對所有 Agent Runtime 採 thin adapter 與 compatibility matrix。

### 7.4 Observability

- structured logs，包含 correlation/proposal/task/run IDs。
- metrics：trigger、proposal、decision、execution、verification、latency、cost。
- trace 不記錄 secret 或未授權的 memory content。

## 8. 架構邊界

1. **Cognitive Layer / AgentMemoryOS**：記憶檢索、分級、共鳴、候選關聯。
2. **Proposal Layer / EngramFlow**：結構化提案，不執行工具。
3. **Policy Layer / EngramFlow**：風險、預算、授權、去重與 idempotency。
4. **Routing Layer / EngramFlow**：依 capabilities、policy 與 workspace 安全選擇 runtime。
5. **Execution Layer / Agent Runtime**：由 Hermes、Claude Code、Codex、AGY、Grok Build 等執行 bounded task。
6. **Reconciliation Layer / EngramFlow**：將 scheduled result/finding 回流 conversation inbox，並建立受治理 remediation proposal。
7. **Verification Layer / EngramFlow**：獨立驗證。
8. **Feedback Layer / AgentMemoryOS**：記錄結果並調整未來聯想。

詳細內容見 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 9. 建議技術結構

```text
bastet-engramflow/
├── src/bastet_engramflow/
│   ├── contracts/
│   ├── triggers/
│   ├── memory_adapter/
│   ├── resonance/
│   ├── proposals/
│   ├── policy/
│   ├── routing/
│   ├── runtimes/
│   │   ├── hermes/
│   │   ├── claude_code/
│   │   ├── codex/
│   │   ├── agy/
│   │   └── grok_build/
│   ├── protocols/
│   │   ├── mcp/
│   │   └── acp/
│   ├── reconciliation/
│   ├── verification/
│   ├── feedback/
│   └── observability/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   └── e2e/
├── docs/
├── examples/
└── pyproject.toml
```

語言與 framework 尚未正式決議。因 Hermes 與目前環境以 Python 為主，MVP 建議 Python 3.11+；最終版本須以 ADR 記錄。

## 10. 狀態模型

```text
observed
  → proposed
  → policy_rejected | awaiting_approval | shadowed | approved
  → queued
  → running
  → worker_reported_done | failed | timed_out | cancelled
  → verifying
  → verified | verification_failed
  → feedback_recorded
```

每次轉換均寫入不可覆寫的事件記錄。重試建立新的 execution attempt，但沿用 proposal 與 idempotency lineage。

## 11. 推進階段

### Phase 0 — Discovery and contracts

交付：

- pin AgentMemoryOS 與各目標 runtime 的 source/version/license
- extension point 與 capability gap matrix
- schema v1
- threat model
- MCP 版本定義
- ADR：語言、儲存、event transport、Agent Runtime SPI 與 adapter seam

完成條件：所有未決技術假設有 owner，核心 contract 可驗證。

### Phase 1 — Shadow mode MVP

交付：

- trigger ingestion
- memory/resonance adapter mock + real sandbox adapter
- proposal generator
- policy engine baseline
- append-only audit store
- dashboard/report for proposal review

完成條件：不執行副作用；可連續運行並量測 precision、duplicate、false-trigger。

### Phase 2 — Low-risk automation

允許範圍：read-only research、health checks、draft、local report artifact。

交付：

- 至少一個 production candidate runtime adapter
- independent verifier
- retry/timeout/cancel
- MCP contract tests

完成條件：所有 execution 均有 verification，且高風險 capability 被 policy test 阻擋。

### Phase 3 — Approval-gated actions

交付：

- user/operator approval flow
- signed/expiring approval token
- approval binding to proposal digest
- staging write actions

完成條件：修改提案後舊 approval 自動失效；audit 可重建完整因果鏈。

### Phase 4 — Limited autonomy

- 依 action class 分別開放，不做全域開關。
- 新 action class 一律回到 shadow mode。
- production write、刪除、支付、權限與公開發布維持明確批准，除非另有經審核政策。

## 12. 測試策略

### Unit tests

- schema validation
- risk classification rules
- dedup/cooldown/budget/idempotency
- ACL filtering
- state transitions

### Contract tests

- AgentMemoryOS retrieval/resonance response
- Agent Runtime task submission/status/cancel/capability discovery
- MCP discovery/call/error mapping
- verifier artifact/read-back contract

### Integration tests

- trigger → proposal → policy → shadow audit
- approved low-risk proposal → selected runtime sandbox → verifier → feedback
- timeout/retry/duplicate/network failure

### Security tests

- prompt injection cannot bypass policy
- memory ACL isolation
- approval replay/tamper
- secret redaction
- high-risk capability denial

### Compatibility tests

- 每個 pinned Supported runtime release
- 每個 runtime latest supported tag
- 各 runtime upstream main/nightly 作為 early-warning lane
- supported MCP compatibility matrix

## 13. CI/CD Gate

每個 pull request 至少執行：

- formatting/lint/type checking
- unit + contract tests
- secret scan
- dependency vulnerability scan
- schema compatibility check
- docs link/check

release gate 另執行 integration/e2e 與 compatibility matrix。未經 verifier 的「agent self-report」不得作為 CI pass 證據。

## 14. 安全發布策略

1. local deterministic tests
2. sandbox integration
3. shadow mode
4. low-risk read-only automation
5. approval-gated staging write
6. action-class-specific production rollout

Rollback 以停用 proposal consumption / action class 為第一選擇，不依賴回滾記憶資料。Audit log 與已發生的外部副作用不可假裝消失。

## 15. 主要風險與緩解

- **False resonance**：shadow mode、threshold calibration、人工標記與 suppression feedback。
- **Duplicate action**：idempotency key、dedup window、external read-back。
- **Privilege escalation**：capability allowlist、separate execution identity、policy tests。
- **Prompt injection**：untrusted content 標記、deterministic policy、tool scope 限制。
- **Agent runtime drift**：thin adapters、pinned versions、capability detection、compatibility CI。
- **MCP version ambiguity**：先定義 compatibility contract，不以「2.0」猜測官方 protocol version。
- **Self-reported success**：獨立 verifier 與 evidence requirement。
- **Memory poisoning**：provenance、ACL、confidence、correction history、append-only feedback。

## 16. 未決策事項

以下事項尚未獲明示，不應假裝已定案：

1. AgentMemoryOS repository/API/schema 與授權。
2. 「MCP 2.0+」實際指 project adapter semantic version、某個 MCP server 產品版本，或 JSON-RPC 2.0。
3. 首個支援的 MCP protocol date/version 與 transports。
4. MVP persistence：SQLite、PostgreSQL 或既有 AgentMemoryOS store。
5. 各 Agent Runtime 首選 integration seam、最低 capability 與支援等級。
6. 部署拓樸與 production owner。
7. 預算與風險閾值。
8. memory resonance scoring 與 feedback learning 規則。

## 17. Definition of Done

一個功能只有在以下條件皆成立時才完成：

- contract/schema 已版本化。
- 實作與測試已通過。
- 權限、風險、timeout、retry 與 idempotency 已處理。
- 可觀測資料不洩漏 secret。
- 執行結果具獨立證據。
- 文件與 compatibility matrix 已更新。
- 變更可停用或回滾。

## 18. 下一個工程 Sprint

1. 完成 `PLAN-008` durable Hermes handoff queue、bounded dispatcher CLI、full gate與independent review。
2. 保持production dispatcher、consumer與現有outbox state不變，直到獨立enablement approval。
3. 設計Hermes gateway queue consumer的stable seam、idempotency與ambiguous external delivery處置。
4. 建立dispatcher/consumer service ownership、health/read-back、backup與rollback runbook。
5. 對現有pending item準備一次性、bounded、可回滾的production approval pack。
