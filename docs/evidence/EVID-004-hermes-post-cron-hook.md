---
id: EVID-004
title: Hermes post-cron hook 與 durable bridge 驗證證據
type: evidence
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-003
related_plans:
  - PLAN-004
related_adrs:
  - ADR-0005
---

# EVID-004：Hermes post-cron hook 與 durable bridge 驗證證據

## Scope

驗證 pinned Hermes `1072c0725115e9be0491ca4cb0d965b9f5f59874` 的 observer-only `post_cron_job` patch、allowlisted shell hook subprocess、Bastet strict bridge、SQLite durable enqueue、restart/replay與original Telegram thread preservation。Production checkout、config與services均未修改。

## TDD Evidence

1. RED：Hermes focused fixture在patch前2 tests失敗，`tick()`只有`mark`且沒有hook。
2. GREEN：加入hook registry、post-persistence emitter與fail-open wrapper後，focused hook tests與128項scheduler regression通過。
3. RED：Bastet bridge module不存在，targeted unittest以`ModuleNotFoundError`失敗。
4. GREEN：bridge、CLI、strict schema、durable bounds與subprocess tests完成。
5. Review remediation：新增basename-only artifact reference、unknown-field fail-closed、failure/delivery/soft-failure fixtures、真scheduler跨process E2E與README/manifest drift gate。

## Pinned Artifact

- Base commit：`1072c0725115e9be0491ca4cb0d965b9f5f59874`
- Patch：`integrations/hermes/patches/1072c0725-post-cron-job-hook.patch`
- SHA-256：`2fa36a110d7dcf9a3fb5846ede59c95a5162edbea6f4c792b7026079a7d30c5b`
- Clean `git apply --check`：exit 0。
- Applied source `py_compile`與`git diff --check`：exit 0。

## Hermes Verification

在fresh detached worktree `/tmp/hermes-patch-verify`套用artifact後執行：

```bash
BASTET_REPO_ROOT=/mnt/nas/Hermes-Gitlab/Bastet-EngramFlow \
python3 -m pytest \
  tests/cron/test_post_cron_hook.py \
  tests/cron/test_shell_bridge_e2e.py \
  tests/cron/test_scheduler.py \
  tests/agent/test_shell_hooks.py \
  tests/agent/test_shell_hooks_consent.py -q
```

結果：211 passed，1個Python `audioop` deprecation warning；exit 0。

覆蓋：

1. 每個`_process_job()` success/soft-failure/exception path最多emit一次，且`mark_job_run()`先於hook。
2. Hook callback exception不改變既有cron結果。
3. Delivery error、runner exception與soft failure payload正確。
4. Prompt不跨boundary；result text redacted/bounded。
5. Output artifact只傳sanitized basename，不洩露host-local absolute path。
6. 真實patched `tick()`經Hermes shell serializer與subprocess呼叫Bastet CLI，SQLite read-back保留Telegram chat/thread。
7. 相同payload重播只保留一個durable event。

額外`tests/hermes_cli/test_plugins.py`全檔有2項失敗；同一commit未套patch的baseline worktree執行相同2項亦失敗，原因為本機額外`agent-memory-os` plugin discovery污染，判定非patch regression，未列為通過宣稱。

## Bastet Final Gate

2026-08-05 12:37 CST執行：

```bash
ruff format --check .
ruff check .
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
python3 scripts/check_docs.py
python3 -m compileall -q src scripts tests integrations/hermes/tests
git diff --check
```

結果：

- Ruff format：31 files already formatted。
- Ruff check：All checks passed。
- Unit/governance：63 tests，全部通過。
- Documentation governance：PASS。
- Compileall：exit 0。
- Git diff check：exit 0。

## Security / Durability Contracts

- Wire與payload unknown fields fail closed；Hermes observer telemetry field列入known schema。
- Input stdin上限1 MiB；result/error/receipt採character或UTF-8 byte bounds。
- Output artifact URI只保存sanitized basename。
- SQLite run/decision/outbox同transaction；invalid input不建立partial ledger。
- UUID只保證單一emitted payload identity；同payload replay去重，不宣稱跨job re-execution identity或exactly-once。

## Limitations

- 未修改或重啟production Hermes checkout/service。
- 未執行真實Telegram API delivery；驗證範圍是original thread metadata經scheduler→shell→SQLite的read-back。
- Production deployment需另行核准、snapshot、preflight、smoke/read-back與rollback演練。
