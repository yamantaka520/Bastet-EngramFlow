---
id: DOC-TRACE-001
title: 可追溯性規範
type: traceability
status: active
owner: project-maintainers
created: 2026-08-05
updated: 2026-08-05
---

# 可追溯性規範

## 1. 必要追溯鏈

Bastet-EngramFlow 的每個交付物至少應能形成：

```text
GOAL → STAGE → PLAN → ADR/SPEC → IMPLEMENTATION → EVIDENCE → REVIEW/STATUS
```

不是每次變更都需要新增 ADR，但每個實作與證據都必須能追溯至 active plan。

## 2. 關聯欄位

治理文件 front matter 使用：

- `related_goals`
- `related_stages`
- `related_plans`
- `related_adrs`
- `related_evidence`
- `supersedes`
- `superseded_by`

每個引用的 ID 必須存在；不可使用模糊名稱取代 ID。

## 3. Commit 與證據

- Commit subject 使用 `type: summary`。
- Commit body 建議加入 `Plan: PLAN-NNN`、`Goal: GOAL-NNN`。
- Evidence 應記錄執行命令、exit code、結果摘要、環境限制與對應 commit/working tree 狀態。
- 無法重現或只來自 Agent 自述的內容必須標記 limitation，不可作為唯一驗收證據。

## 4. 狀態一致性

- `PROJECT_STATUS.md` 是目前狀態的唯一總覽。
- 詳細內容以 Goal、Stage、Plan、ADR、Evidence 原文件為準。
- 狀態總覽與詳細文件衝突時，視為治理缺陷，必須在合併前修正。
- `accepted` 代表驗收條件有證據支持，不等同單純寫完文件或程式。

## 5. 階段追溯矩陣

| Goal | Stage | Plan | ADR | Evidence | 狀態 |
|---|---|---|---|---|---|
| GOAL-001 | STAGE-000 | PLAN-001 | 0001, 0002 | EVID-001 | accepted |
| GOAL-001 | STAGE-001 | PLAN-002 | 0003 | EVID-002 | accepted |
| GOAL-001 | STAGE-002 | PLAN-003 | 0004 | EVID-003 | accepted |
| GOAL-001 | STAGE-003 | PLAN-004 | 0005 | EVID-004 | accepted |
| GOAL-001 | STAGE-004 | PLAN-005 | 0005 | EVID-005 | accepted |
| GOAL-001 | STAGE-005 | PLAN-006 | 0005 | EVID-007 | accepted |

## 6. 自動化檢查目標

文件治理檢查器至少驗證：

1. 規範目錄下檔名與 ID 格式。
2. 必要 front matter 欄位。
3. Plan 對 Goal/Stage 的引用存在。
4. Active/blocked/review 文件出現在 status。
5. Superseded 文件具替代目標。
6. Markdown 內部連結有效。
7. Compatibility 的 Supported 列具 evidence reference。
