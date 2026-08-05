# ADR-0002：Repository-native 文件治理與穩定追溯 ID

- Status：Accepted
- Date：2026-08-05
- Decision owners：Project maintainers
- Related：GOAL-001、STAGE-000、PLAN-001

## Context

專案要求開發過程、計畫、目標、達成階段與驗證結果全程有跡可循。聊天記錄與 Agent memory 可協助工作延續，但不是可審核、可版本化的唯一事實來源；多 Agent 也不能假設能存取同一份會話資料。

## Decision Drivers

- 人類與不同 Agent 都能使用。
- Git diff 可審核並保留歷史。
- 狀態、目標、計畫與證據具有穩定 ID。
- 能以 CI 自動檢查引用與必要欄位。
- 不依賴專有 SaaS 或單一 Agent runtime。

## Options Considered

### A. 只使用 Issues/PR

無法保證離線可用，也會把核心知識綁定 hosting provider。

### B. 只使用 Wiki 或聊天記憶

難以與程式 diff、commit 與 release evidence 建立強關聯。

### C. Repository-native Markdown + front matter + CI

使用 Git 版本化治理文件，外部 issue/wiki 可作視圖或協作入口，但 repository 保持 canonical record。

## Decision

採用 Option C。

1. Goal、Stage、Plan、Evidence、Review 與 ADR 置於 `docs/` 固定目錄。
2. 文件使用穩定 ID；ID 不因改名而重用。
3. `PROJECT_STATUS.md` 為目前狀態唯一總覽。
4. `COMPATIBILITY_MATRIX.md` 為支援聲明唯一來源。
5. Accepted 必須有 evidence；Agent self-report 不構成 evidence。
6. 文件治理規則由 `docs/GOVERNANCE.md` 定義，追溯規則由 `docs/TRACEABILITY.md` 定義。
7. CI/本機檢查器驗證必要欄位、引用、狀態與文件連結。
8. 外部 issue、PR、Kanban 或 Wiki 可引用這些 ID，但不得取代 repository canonical record。

## Consequences

### Positive

- 可由 Git 重建完整專案脈絡。
- 多 Agent 取得一致、vendor-neutral 的 project context。
- 目標、變更與 evidence 可機器驗證。
- 適合離線與開源協作。

### Negative

- 每個工程增量需同步文件。
- 若沒有自動檢查，狀態文件可能漂移。
- 過度細分文件會增加負擔，因此第一階段只建立必要類型。

## Verification

- `scripts/check_docs.py` 能檢查必要文件、front matter 與引用。
- Active plan 必須出現在 `PROJECT_STATUS.md`。
- Plan 必須連結 Goal 與 Stage。
- Accepted plan 必須連結 Evidence。
- Broken reference 會使檢查失敗。

## Rollback / Supersession

治理系統可由後續 ADR 改為其他 canonical store，但必須保留 stable IDs、Git 可稽核歷史與遷移映射。
