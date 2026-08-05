---
id: EVID-011
title: Hermes context consumer production artifact readiness evidence
type: evidence
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-009
related_plans:
  - PLAN-010
related_adrs:
  - ADR-0004
  - ADR-0005
---

# EVID-011 — Hermes Context Consumer Production Artifact Readiness

## Environment

- Repository: `/mnt/nas/Hermes-Gitlab/Bastet-EngramFlow`
- Branch: `feat/hermes-production-reconciliation-hook`
- Evidence timestamp: 2026-08-05 19:25:50 CST（UTC+8）
- Production mutation: none

## Read-only Production Preflight

- Service: `hermes-bastet.service`; owner`bastet`; state active/running; ExecStart使用`/home/bastet/.hermes/hermes-agent/venv/bin/hermes gateway run`。
- Service environment只有`BASTET_RECONCILIATION_DB`，沒有`BASTET_HERMES_DELIVERY_DB`或consumer owner設定。
- Live Hermes HEAD：`d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`。
- Existing post-cron patch verifier：variant`production-d0c0a6b`、patch SHA-256`af1d421f0b33ee06e14dae9bfca20e4c5490e13c28f78b76dbb9979614cc65dc`、state`applied`。
- Live dirty paths精確為`cron/scheduler.py`、`hermes_cli/plugins.py`與source-pinned`tests/cron/test_post_cron_hook.py`；test fixture與repository artifact byte-identical。
- `agent/turn_context.py`目前傳`turn_id/platform/sender_id`，尚未傳`conversation_id/thread_id`；agent有`_chat_id/_thread_id`來源。
- State filesystem read-back為local ext-family；state owner`bastet`，integration directory mode`0700`，source DB mode`0600`，delivery DB absent。
- Source DB read-only integrity check`ok`；`reconciliation_outbox`有1筆`pending`、attempts 0、無lease/delivery；`hermes_context_inbox` absent。既有item不得自動採用為canary。

## Plugin RED → GREEN

Initial focused command在artifact不存在時回報5 failures，涵蓋manifest、missing env、relative/missing/uninitialized DB、unsafe mode及exact routing。

實作後：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. \
  python3 -m pytest -o 'addopts=' -p no:cacheprovider -q \
  tests/test_hermes_context_plugin.py
```

Result：5 tests PASS。驗證中發現`immutable=1`會忽略尚在WAL內的合法schema；改為SQLite`mode=ro`後可讀取WAL且仍不執行schema mutation。

## Source-pinned Patch RED → GREEN

- Hermes base：`d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`
- Changed path：只有`agent/turn_context.py`
- Patch SHA-256：`1741f6c7d77d0cb13c1dfcb74cb8acc18a5db054a2999fb6c588bc075c4f1eda`
- Added kwargs：`conversation_id=getattr(agent, "_chat_id", None)`與`thread_id=getattr(agent, "_thread_id", None)`。

在isolated exact clone reverse patch後，兩項routing execution tests因缺`conversation_id`而2/2 RED；reapply後canonical runner結果：

```text
artifact verifier state=applied
3 passed
```

三項source-pinned tests包含threaded/threadless kwargs、missing conversation不使用sender fallback，以及真實Hermes`PluginManager`plugin load/invoke。

## Artifact Verification

- Live production tree：verifier state`applicable`，production prerequisite dirty paths精確匹配。
- Isolated patched tree：verifier state`applied`。
- Plugin init SHA-256：`825d5179d8150a9e3049028f3e1cbc8088b1810e282d2faaa8169fac88ff2b67`
- Plugin manifest SHA-256：`08e26d49ff8343ae1ca31736dcb096fb6262f1dba1729bf17e78d6b1d17199e2`
- Reproducible wheel：`bastet_engramflow-0.1.0.dev0-py3-none-any.whl`，SHA-256`3791465422639feb80e8a6fd459cb575839029bcf1cad28a871e105379c018d7`；以isolated source copy及`SOURCE_DATE_EPOCH=315532800`重建兩次，byte-identical；clean venv plugin registration smoke PASS。
- Artifact manifest同時固定source-pinned tests與existing bridge prerequisite digest。

## Production Boundary

未修改live Hermes checkout、plugin/config/systemd/venv；未建立delivery DB；未claim或transition source/delivery row；未restart service；未觸發真實conversation或platform API。Repository artifact readiness不等於production approval。

## Closure Evidence

- Focused verifier/plugin/consumer/dispatcher：`29 passed`
- Canonical repository suite：`100 passed`
- Source-pinned compatibility runner：`3 passed`
- Ruff format/lint、compileall、documentation governance：PASS
- Live production verifier：context patch`applicable`；existing prerequisite integration/variant/digest/content/state`applied`
- Reproducible wheel verifier與clean venv smoke：PASS
- Final independent review：High 0 / Medium 0 / Low 2 non-blocking；repository artifact readiness ACCEPT
- Publication仍須commit、push與remote SHA read-back；此步只發布repository artifacts，不授權任何production mutation。
