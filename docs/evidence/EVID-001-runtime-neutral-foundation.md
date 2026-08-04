---
id: EVID-001
title: Runtime-neutral foundation 驗證證據
type: evidence
status: review
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-000
related_plans:
  - PLAN-001
---

# EVID-001：Runtime-neutral foundation 驗證證據

## Claim

`PLAN-001` 的 runtime-neutral SPI 與文件治理骨架可由 repository 內命令重現驗證。

## Environment

- Python：3.11.15
- Branch：`feat/runtime-neutral-foundation`
- Base commit：`baf70db78d91495e455fec7990ab36d2b42216db`
- 時區：Asia/Taipei（UTC+8）

## RED Evidence

在 production source 尚未建立時執行：

```text
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

結果：exit code `1`，兩個 test module 均因 `ModuleNotFoundError: No module named 'bastet_engramflow'` 失敗，證明測試先於實作生效。

文件治理測試在 `scripts` 尚未建立時執行：

```text
PYTHONPATH=src:. python3 -m unittest tests.test_documentation_governance -v
```

結果：exit code `1`，`ModuleNotFoundError: No module named 'scripts'`。

## GREEN Evidence

建立 runtime models、SPI 與 registry 後執行：

```text
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

第一版結果：11 tests，全部 `OK`，exit code `0`。

完成獨立 review 第一輪提出的 capability mismatch、invalid handle 與 Supported/evidence gate 缺口後，於 2026-08-05 07:43 CST 執行：

```text
ruff format --check src scripts tests
ruff check src scripts tests
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
python3 scripts/check_docs.py
python3 -m compileall -q src scripts tests
git diff --check
```

結果：

- Ruff format：11 files already formatted。
- Ruff lint：All checks passed。
- Unit/governance tests：最終 19 tests，全部 `OK`，exit code `0`。
- Documentation governance：`PASS`。
- Compileall：exit code `0`。
- Git diff check：exit code `0`。

Negative tests 已證明 checker 可偵測不存在的治理 ID、broken Markdown link 與缺少 EVID reference 的 Supported claim。

## Audit Evidence

- Core vendor identifier/import search：0 matches。
- Secret assignment/private-key marker search：0 matches。
- 本機絕對路徑、`.pem` 與 token assignment 文件搜尋：0 matches。
- 第一輪獨立 review：0 High、2 Medium、2 Low。
- 第二輪 read-back：0 High、1 Medium；發現 adapter-side unknown execution ID 尚未以 executable contract test 證明。
- 第二輪修正：FakeRuntime 將 wrong runtime/unknown execution ID 正規化為 `InvalidExecutionHandleError`，並新增 adapter contract negative test；完整測試增為 19 項。

## Limitations

本證據為 review 狀態；待修正後的第二輪獨立 review 與 commit read-back。它不構成任何真實 Agent adapter 的 Supported 聲明。
