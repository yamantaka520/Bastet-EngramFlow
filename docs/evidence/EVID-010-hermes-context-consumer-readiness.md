---
id: EVID-010
title: Fail-closed Hermes context consumer readiness evidence
type: evidence
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-008
related_plans:
  - PLAN-009
related_adrs:
  - ADR-0004
  - ADR-0005
---

# EVID-010 — Fail-closed Hermes Context Consumer Readiness

## Environment

- Repository: `/mnt/nas/Hermes-Gitlab/Bastet-EngramFlow`
- Branch: `feat/hermes-production-reconciliation-hook`
- Evidence timestamp: 2026-08-05 18:46:11 CST（UTC+8）
- Production mutation: none

## Read-only Discovery

- Development and production Hermes source both expose`pre_llm_call` and pass an existing per-turn `turn_id`.
- Production exact callsite is`agent/turn_context.py`; it passes`platform` and`sender_id` but not conversation/thread routing.
- Production agent initialization stores`_chat_id` and`_thread_id`; a future compatibility patch can pass those two values without changing gateway semantics.
- `hermes-bastet.service` read-back: owner`bastet`; ExecStart uses the Bastet Hermes venv; current environment contains only the source reconciliation DB for this integration and no delivery queue/consumer configuration.
- Production Hermes read-back: pinned HEAD`d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`; only the previously governed`cron/scheduler.py` and`hermes_cli/plugins.py` patch paths are modified. No STAGE-008 path was changed.

## Initial RED

Command:

```bash
PYTHONPATH=src:. python3 -m unittest tests.test_hermes_context_consumer -v
```

Result: exit`1`; ImportError confirmed the new public consumer/state API did not exist.

## Initial GREEN

Implemented:

- additive queue state/lease migration in`delivery_queue.py`
-`HermesPreLLMContextConsumer` callback in`context_consumer.py`
- public exports
- initial seven focused consumer tests

Combined consumer plus dispatcher result: 17 tests PASS.

## Independent Review Round 1

Fresh-context review reported High 0 / Medium 1. The Medium finding showed that`thread_id=""` was downgraded to`None`, which could claim a threadless row instead of failing closed. Review also requested legacy consumed-row, platform/threadless isolation and escaping regressions.

During regression design, engineering identified an additional migration defect: SQLite`ADD COLUMN state DEFAULT 'pending'` populates legacy rows before the original conditional mapping, so an already-consumed legacy row remained pending.

## Review-fix RED

Expanded focused command reproduced exactly two failures:

- empty thread routing returned context and consumed a threadless row
- legacy`consumed_at IS NOT NULL` row migrated to`pending`

## Review-fix GREEN

Fixes:

- Explicitly reject a provided but empty`thread_id` before queue access.
- Explicitly map legacy consumed rows to`delivered` and backfill`delivered_at` from`consumed_at`.
- Added platform/threadless exact routing and fence-closing markup escaping tests.

Final focused command at this point:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. \
  python3 -m unittest \
  tests.test_hermes_context_consumer \
  tests.test_reconciliation_dispatcher -v
ruff check src/bastet_engramflow/reconciliation \
  tests/test_hermes_context_consumer.py \
  tests/test_reconciliation_dispatcher.py
```

Result: exit`0`; 20 tests PASS; Ruff lint PASS.

## Formatting Environment Limitation

NAS permissions prevent the terminal identity from rewriting repository files. `ruff format --diff` was therefore used as a read-only formatter oracle and its exact targeted changes were applied through the controlled patch tool. No chmod/chown or shared-storage permission change was performed.

## Production Boundary Read-back

No production dispatcher execution, delivery DB creation, queue claim/transition, plugin/config/source mutation, service restart or platform call occurred. The production compatibility patch and plugin registration remain explicit inputs to a separate approval stage.

## Broad Pytest Invocation Incident

A broad repository-root`pytest` invocation collected 14 source-pinned Hermes integration fixtures without their required variant runner. They imported the ambient`/home/neo/.hermes/hermes-agent` source and lacked`BASTET_REPO_ROOT`, producing 14 harness/environment failures while the 91 core tests passed. No production source or service was modified. The canonical repository gate was rerun explicitly against`tests/` with pinned`PYTHONPATH` and cache disabled.

## Closure Evidence

```bash
ruff format --check src tests integrations scripts
ruff check src tests integrations scripts
PYTHONPYCACHEPREFIX=/tmp/bastet-stage8-pycache \
  python3 -m compileall -q -f src tests integrations scripts
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python3 scripts/check_docs.py
BASTET_REPO_ROOT=/mnt/nas/Hermes-Gitlab/Bastet-EngramFlow \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/mnt/nas/Hermes-Gitlab/Bastet-EngramFlow/src:. \
python3 -m pytest -o 'addopts=' -p no:cacheprovider -q tests
```

Results：42 files formatted；Ruff lint PASS；compileall PASS；documentation governance PASS；91 tests PASS。Final independent review確認Round 1 finding關閉，High 0 / Medium 0 / Low 2 non-blocking，repository readiness ACCEPT，production approval WITHHELD。

Commit、push與remote SHA read-back於publication closure執行並在外部回報；本文件不預先聲稱尚未完成的Git結果。
