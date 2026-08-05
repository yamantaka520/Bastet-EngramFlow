# ADR-0003：Scheduled Execution 以 Reconciliation Event 回流 Conversation

- Status：Accepted
- Date：2026-08-05
- Decision owners：Project maintainers
- Related：GOAL-001、STAGE-001、PLAN-002

## Context

排程任務為了隔離、可重試與長時間執行，通常在新的 agent session/process 中運作。這可避免污染互動 session，卻也使 run 中發現的問題、結果與 artifact 無法自然進入原 conversation；排程 agent 也無法安全地在原 session 中展開討論或延伸修復。

直接 resume 或改寫原 conversation session store 會綁定 vendor schema、破壞 message ordering/prompt cache，並讓未受信任的 scheduled output 取得過高權限。

## Decision Drivers

- 排程與對話執行保持隔離。
- 結果與問題仍可主動回流到原 conversation/thread。
- 回流、提案與後續執行都必須可追溯、去重與受 policy 約束。
- 不假設跨 runtime 原生 session 可攜。
- 不允許 worker 自行宣稱修復已 verified。

## Options Considered

### A. 讓 cron 直接 resume 原 session

上下文最直接，但會耦合 vendor session、引入並行寫入與訊息序列風險。

### B. 只將 final text 發送到聊天平台

容易實作，但結果無 structured lineage、問題分類、deduplication、proposal 與 verification contract。

### C. Structured reconciliation event + governed remediation proposal

排程 run 產生 runtime-neutral envelope；core 建立 conversation context event 與可選 remediation proposal，再由 inbox、policy gateway、runtime router 與 verifier 接續。

## Decision

採用 Option C。

1. Scheduled runner 完成或遇到問題時，提交 `ScheduledRunEnvelope`，包含 schedule/run identity、origin conversation、outcome、findings、artifacts 與 continuation depth。
2. Reconciler 產生不可變的 `ConversationContextEvent`；透過 `ConversationInbox` port 投遞，不直接改寫 vendor session history。
3. Retryable finding 可形成 `RemediationProposal`，但只標記 eligibility；真正執行仍需 policy gateway/runtime router。
4. External side effect、critical severity、缺少 idempotency key 或超出 depth 一律 approval-gated。
5. `(schedule_id, run_id)` 是 deduplication key；reference coordinator 只保證單一 process/instance 範圍。只有 inbox/proposal sink 均成功後才完成 local commit，失敗以 stable IDs 重試；production 跨重啟／多實例需 durable ledger/outbox。
6. Conversation event 內容是 data，不可被當成 system instruction；adapter 必須處理 redaction、size limits 與 provenance。
7. 後續修復結果會形成新的 run/event，保留 parent run/proposal lineage，不在原事件上覆寫為 resolved。

## Consequences

### Positive

- Scheduled run 保持隔離，結果仍能主動進入對話討論。
- 問題可形成 bounded、auditable 的主動修復流程。
- 可跨 Hermes、Claude Code、Codex、AGY、Grok Build 使用相同核心 contract。
- Sink failure、duplicate delivery 與 unsafe replay 有明確語意。

### Negative

- 需要 durable inbox/outbox 與 ledger adapter 才能達到 production reliability。
- Conversation 可能收到更多事件，需要聚合、cooldown 與優先級策略。
- 不能直接延續 vendor 原生 reasoning state，只能透過 portable event/context bundle 接續。

## Verification

- Contract tests 驗證 success/failure 回流、deduplication、sink retry 與無 origin 行為。
- Policy tests 驗證 critical/external/non-idempotent/depth gates。
- Worker completion、proposal created 與 verified 三種狀態保持分離。

## Rollback / Supersession

若 production adapter 證明 inbox/event 模型不足，新增 ADR supersede；不得退回未治理的原 session mutation。
