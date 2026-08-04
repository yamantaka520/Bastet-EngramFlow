---
id: DOC-GOV-001
title: 文件與交付治理規範
type: governance
status: active
owner: project-maintainers
created: 2026-08-05
updated: 2026-08-05
---

# 文件與交付治理規範

## 1. 目的

Bastet-EngramFlow 採文件即控制面的治理方式。專案目標、階段、計畫、架構決策、實作證據與審查結論必須能由 repository 內的版本化文件重建，不以聊天記錄、Agent 自述或未提交的暫存內容作為唯一依據。

## 2. 治理來源

- `docs/goals/`：長期目標與成功條件。
- `docs/stages/`：階段、進入條件與退出條件。
- `docs/plans/`：可執行工作計畫、交付物及驗收條件。
- `docs/adr/`：具長期影響的架構決策。
- `docs/evidence/`：測試、稽核、相容性與外部 read-back 證據。
- `docs/reviews/`：階段、版本或重大變更的獨立審查。
- `docs/PROJECT_STATUS.md`：目前唯一的專案狀態總覽。
- `docs/TRACEABILITY.md`：ID、關聯與追溯規則。
- `docs/COMPATIBILITY_MATRIX.md`：唯一的 runtime/protocol 支援聲明來源。

聊天記憶屬於 remembered；寫入檔案才是 materialized；Git commit 後才是 versioned；推送並從 remote 驗證後才是 published。

## 3. 穩定識別碼

| 類型 | 格式 | 例子 |
|---|---|---|
| Goal | `GOAL-NNN` | `GOAL-001` |
| Stage | `STAGE-NNN` | `STAGE-000` |
| Plan | `PLAN-NNN` | `PLAN-001` |
| Evidence | `EVID-NNN` | `EVID-001` |
| Review | `REVIEW-NNN` | `REVIEW-001` |
| ADR | `NNNN` | `0001` |

ID 建立後不可重用。檔名 slug 可調整，但文件內的 ID 不可改。

## 4. 文件狀態

通用狀態：

- `draft`：尚在撰寫，不可作為已定案依據。
- `proposed`：可供審查的提案。
- `active`：已採用且正在執行。
- `blocked`：因明確阻擋暫停，必須記錄解除條件。
- `review`：交付物已形成，等待證據或審查。
- `accepted`：已通過驗收。
- `rejected`：已審查但不採用。
- `superseded`：由新文件取代，必須連結替代文件。
- `archived`：已結束且不再作用。

合法主要轉移：

```text
draft → proposed → active → review → accepted → archived
                    ↕
                  blocked

proposed → rejected
accepted → superseded
```

## 5. 強制規則

1. 每個 active plan 必須關聯至少一個 Goal 與一個 Stage。
2. 每個 plan 必須列出 deliverables、acceptance criteria、risks 與 verification。
3. 架構、protocol、安全邊界或不可逆相容性決策必須有 ADR。
4. `worker_reported_done`、Agent 最終文字或 CLI exit code 不能單獨構成 accepted。
5. accepted plan 必須有 `docs/evidence/` 中的證據，並連結 review 或狀態紀錄。
6. 所有 active、blocked、review 項目必須出現在 `PROJECT_STATUS.md`。
7. 支援聲明只能由 `COMPATIBILITY_MATRIX.md` 發布，且必須有真實 contract/E2E evidence。
8. 重大範圍變更需更新 Goal、Stage、Plan、ADR 與 status 中受影響的部分，不得只修改其中一份。
9. 所有時間採 ISO 8601；人類閱讀時間使用 UTC+8，機器事件建議同時保存 RFC3339 offset。
10. secrets、tokens、私鑰路徑與 production payload 不得寫入治理文件或證據。

## 6. 每次變更的最小交付鏈

```text
Goal / Stage
  → Plan
  → ADR or specification（需要時）
  → implementation / documentation diff
  → Evidence
  → Review
  → PROJECT_STATUS update
```

## 7. Pull Request / Commit gate

提交前至少確認：

- 對應 plan 狀態與交付物已更新。
- 新行為具測試，且保留 RED/GREEN 證據或可重現驗證。
- 文件引用、ID 與狀態一致。
- compatibility claim 有 evidence。
- threat model 與 security governance 已評估。
- `PROJECT_STATUS.md` 反映真實狀態。
- Git diff 不含 secret 或非預期 artifact。

CI 將逐步自動化上述規則；在自動化完成前，由 reviewer 依相同規則人工檢查。
