# ADR-0004：SQLite Durable Ledger/Outbox 與 At-Least-Once Delivery

- Status：Accepted
- Date：2026-08-05
- Decision owners：Project maintainers
- Related：GOAL-001、STAGE-002、PLAN-003

## Context

STAGE-001 的 coordinator 只在單一 process memory 中記錄 completed run。Process restart、多 worker 或 sink partial failure 會失去 deduplication state。Production reconciliation 需要先 durable 記錄 decision，再由可恢復 worker 投遞 event/proposal。

Hermes cron `_process_job()` 已能提供 execution result、final response、output file 與 delivery error；Hermes 另有 best-effort `gateway.mirror.mirror_to_session()`，但直接 append vendor session database 不符合 runtime-neutral 與 message ordering 邊界。

## Decision Drivers

- Python 3.11 stdlib 可執行，不新增 deployment dependency。
- Run 與 outbox 建立必須 atomic。
- Restart、partial failure 與 expired worker claim 可恢復。
- 不對 external sink 做虛假 exactly-once 宣稱。
- Adapter 不依賴 Hermes private session schema。

## Options Considered

### A. 繼續 process-local set

最簡單，但 restart 後 dedup 與 partial progress 全失效。

### B. 直接 mirror 到 Hermes session SQLite

可讓內容出現在 session history，但 best-effort、vendor coupled，且可能破壞 conversation ordering；無法提供 event/proposal 個別 receipt 與 retry state。

### C. SQLite run ledger + transactional outbox + thin adapters

先在 EngramFlow DB atomic enqueue，再以 lease worker 對 idempotent sink 做 at-least-once delivery。Hermes hook 只負責提交 structured result；conversation ingress adapter 自行消費 event。

## Decision

採用 Option C。

1. `(schedule_id, run_id)` 為 run ledger key，保存 canonical payload digest。
2. 相同 key/same digest 是 duplicate；same key/different digest 是 `IdempotencyConflictError`。
3. Event 與 proposal 各自建立 stable outbox item，已 ack item 不重送。
4. Claim 使用 owner + lease deadline；ack/fail 必須 compare owner。
5. Expired lease 可 reclaim，attempt count 遞增。
6. Delivery 是 at-least-once。Sink 成功後、ack 前 crash 可能 duplicate；sink 必須以 event/proposal stable ID 去重。
7. SQLite 適用單機或具正確 filesystem locking 的單 DB deployment；不宣稱一般 NFS/multi-host distributed queue 安全。
8. Hermes adapter 接受 plain structured data，不 import Hermes scheduler/gateway private modules，也不直接寫 session store。
9. Cron final text 視為 untrusted data；adapter 執行 secret redaction、control-character normalization 與 size limit。

## Consequences

### Positive

- Restart 後保留 dedup、attempt、receipt 與 partial progress。
- 不需要 Redis/PostgreSQL 即可完成單機 production candidate。
- Adapter seam 可先測試，再由 Hermes upstream hook 接線。

### Negative

- Sink 必須實作 idempotency；無法消除 crash window duplicate。
- SQLite write throughput 與 multi-host topology 有限制。
- 尚需 production hook、real thread delivery read-back 與 operations policy 才能啟用。

## Verification

- Restart duplicate、conflicting payload、expired lease、stale owner、partial success tests。
- WAL/busy timeout/schema read-back。
- Hermes success/failure/delivery-error mapper、redaction、truncation tests。
- Independent review 確認沒有 exactly-once 或 production-supported 過度聲明。

## Rollback / Supersession

停用 dispatcher 即可停止 external delivery；ledger/outbox 保留。未來若改 PostgreSQL/Kafka，新增 ADR supersede 並提供 migration/read-back evidence。
