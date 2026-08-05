# 安全與治理

## 1. 治理目標

記憶共鳴只能產生「候選行動」，不能直接取得執行權。Bastet-EngramFlow 以 deterministic policy、capability scope、approval binding 與 independent verification 建立安全邊界。

## 2. 風險分級

### Low

- read-only search
- health/readiness check
- local draft/report
- sandbox calculation

可在 shadow mode 驗證後逐類開放。

### Medium

- 對內訊息草稿／受限發送
- 建立 issue/task
- staging write
- 有成本但可控的 API call

原則上需明確 policy、budget 與可回滾設計；初期要求批准。

### High

- production configuration/write
- service restart
- 權限修改
- 對外公開發文
- 大額或不可預測成本

必須人工批准、proposal digest binding 與執行後 read-back。

### Critical

- 刪除不可恢復資料
- 支付／轉帳
- credential rotation/revocation
- 安全控制停用
- 可能造成廣泛服務中斷的操作

預設禁止自動執行。若未來開放，需專用 runbook、雙重批准與 break-glass audit。

## 3. 強制控制

- fail closed：policy/audit/approval 不可用時拒絕副作用。
- least privilege：每種 action class 使用最小 capability。
- project isolation：memory、proposal、execution 不可跨 project 泄漏。
- secret isolation：credential 不得寫入 Git、prompt、memory evidence 或一般 log。
- immutable lineage：trigger → proposal → decision → run → verification → feedback。
- runtime isolation：每個 run 綁定 runtime/adapter version、effective capabilities、workspace 與 execution identity。
- clean fallback：具 workspace write 的跨 Agent fallback 必須使用乾淨 worktree/checkpoint，不得接手未驗證 dirty state。
- approval expiry：批准具 TTL，且只對特定 digest 有效。
- idempotency：重試不可重複副作用。
- evidence gate：未驗證不得標記完成。
- scheduled return isolation：排程結果只能以 structured data event 進入 conversation inbox，不得直接改寫或跨 runtime resume 原 session store。
- remediation boundary：core 只判斷 auto-remediation eligibility；external side effect、critical、non-idempotent 或 depth-exhausted 一律 approval-gated。
- delivery deduplication：conversation event 與 remediation proposal 分別使用穩定 ID，sink 必須支援 idempotent retry。

## 4. Prompt injection 防護

- 外部網頁、文件、tool output、memory text 與 scheduled run summary/finding 一律視為 untrusted data。
- 模型輸出的 risk tier 只供參考，最終由 deterministic rules 判定。
- tool schema 與 capability allowlist 由 runtime 控制，不由 prompt 擴權。
- EngramFlow policy、adapter capability 與 runtime effective permission 取交集；runtime 不得自行宣告新增權限。
- 外部文字中的「忽略規則」「執行命令」不能改變 policy。
- 高風險參數需 normalize、validate 並與批准內容比對。

## 5. Memory safety

- 每筆 memory evidence 保存 provenance、ACL、classification 與 version。
- correction 不覆蓋原紀錄，使用 supersede/append-only event。
- 低可信或來源不明記憶不得單獨觸發高風險 action。
- raw secret 與長篇敏感內容使用 reference/digest，不複製到 proposal。
- feedback reinforcement 不得只依 worker self-rating。

## 6. Audit 最低欄位

- timestamp
- actor / service identity
- project/user scope
- correlation、trigger、proposal、decision、run、verification IDs
- schema/policy/adapter/runtime/protocol/version
- action target 與 capability
- approval identity/digest/expiry（如適用）
- sanitized result/evidence reference
- error/timeout/retry reason

## 7. 資料保留

正式 retention policy 尚待決策。最低要求：

- audit 與業務 payload 分離；
- 可分別配置 retention；
- 刪除或匿名化不破壞必要的安全稽核鏈；
- backup、restore 與 corruption detection 必須測試；
- 個資／敏感資料遵循實際部署法規與組織政策。

## 8. Incident controls

至少提供：

- global proposal consumption pause
- per-action-class kill switch
- per-project disable
- credential revoke path
- queue drain/cancel
- immutable incident export
- last-known-good policy rollback

停止自動化不等於刪除 audit，也不能撤銷已發生的外部副作用；需另行執行補償／回復程序。

## 9. Security release gate

- threat model 已更新
- secret scan 無異常
- dependency scan 已處理
- ACL isolation tests 通過
- prompt injection tests 通過
- high/critical action denial tests 通過
- approval replay/tamper tests 通過
- verifier independence 有證據
- rollback/kill switch 已演練
