---
id: EVID-007
title: Bastet Hermes controlled production rollout evidence
type: evidence
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-005
related_plans:
  - PLAN-006
---

# EVID-007：Bastet Hermes Controlled Production Rollout

## Claim

2026-08-05 14:55–15:10 CST（UTC+8），經使用者明確批准後，`production-d0c0a6b` observer hook與Bastet-EngramFlow bridge已部署到`hermes-bastet.service`。Source、config、exact consent、systemd DB env、private SQLite、gateway-scheduled fixture、origin routing及dedup均有production read-back。Rollout未變更provider/model/credential或其他production jobs。

## Approval boundary

使用者明確選擇：現在執行完整changeset、由小NEO擔任rollback operator、一次性無工具fixture回傳目前Telegram DM `8686567559`。批准前只執行read-only preflight；production mutation自批准後才開始。

## Fixed artifacts

- Bastet-EngramFlow release：`5e2d29a12f60d84c76ca50148ab02a36b798c4bb`
- Production Hermes base：`d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`
- Variant：`production-d0c0a6b`
- Patch SHA-256：`af1d421f0b33ee06e14dae9bfca20e4c5490e13c28f78b76dbb9979614cc65dc`
- Bridge wheel SHA-256：`a83891adcd9e49a26b435f018ba908b3916038be49310b2ef7db86d749f90974`
- Backup：`/home/bastet/.hermes/backups/post-cron-20260805T065148Z`
- Backup manifest SHA-256：`154ab80847f80821910b6bff15fb7c4efab3d0a1c5ebaa5a20289e45ee4f4962`

## Backup and isolated runtimes

- Backup directory owner `bastet:bastet`、mode `0700`。
- Config backup owner `bastet:bastet`、mode `0600`。
- Backup保存config、unit/drop-ins、兩個upstream source files、patch、manifest及metadata checksum；未把config內容或secret寫入evidence。
- Live Hermes venv沒有pytest且未被修改。
- Test runtime由live runtime venv複製到timestamped backup，僅在副本安裝pinned `pytest 9.0.2`與`pytest-asyncio 1.3.0`及其test dependencies。
- Bridge runtime：`/home/bastet/.hermes/bastet-engramflow-venv`，安裝由exact release `git archive`建立的wheel。
- Bridge preflight使用backup內temporary SQLite，exit `0`、`status=enqueued`、stderr empty。

## Rollback trap exercise

第一次source gate在`systemctl stop`後遇到production gateway stop exit `1`，systemd因此將已停止且`MainPID=0`的unit標成`failed`，原gate只接受`inactive`而中止。Rollback trap立即恢復service；read-back為service `active`、Hermes checkout clean、patch `applicable`、HEAD未變。

Gate修正為要求`MainPID=0`且state非`active`，再執行`systemctl reset-failed`。這次演練證明pre-config rollback能reverse source（若已套用）並恢復service；RUNBOOK-001同步記錄此production stop quirk。

## Source deployment gate

- Service停止後`MainPID=0`。
- Verifier post-apply：`state=applied`。
- Changed paths只包含：
  - `cron/scheduler.py`
  - `hermes_cli/plugins.py`
  - `tests/cron/test_post_cron_hook.py`
- Isolated target-tree gate：`358 passed, 1 warning in 15.77s`。
- Warning為既有test process中的`coroutine '_send_to_platform' was never awaited` runtime warning；exit code為`0`。
- Production checkout保持base HEAD，以上三個manifest-owned paths為預期local patch state。

## Config, consent, state and service

- Config以same-directory temporary file + `os.replace`更新，mode `0600`。
- Hook command：`/home/bastet/.hermes/bastet-engramflow-venv/bin/bastet-hermes-post-cron`
- Hook event：`post_cron_job`
- Timeout：`30s`
- `hooks_auto_accept=false`
- Consent allowlist只含1筆exact event/command pair，allowlist及lock均owner `bastet:bastet`、mode `0600`。
- State directory：`/home/bastet/.hermes/state/bastet-engramflow/`，owner `bastet:bastet`、mode `0700`。
- SQLite：`reconciliation.sqlite3`，owner `bastet:bastet`、mode `0600`。
- Systemd只新增`bastet-engramflow.conf`，owner `root:root`、mode `0644`，內容只設定`BASTET_RECONCILIATION_DB`。
- Restart後service `active/running`，MainPID `2371863`；agent log確認shell hook已register。

## Fixture attempts and diagnostic corrections

所有fixture都使用相同固定stdout script `BASTET_STAGE5_POST_CRON_FIXTURE_OK`、`no-agent`、無tools/LLM/network；執行後job及script已清除。

1. `6e69388c4085` / execution `c8ac82a113bc4030b5fa8f8b2a94e066`：CLI direct run。Telegram delivery成功，但direct CLI process不繼承systemd-only DB env，hook fail-open回報`BASTET_RECONCILIATION_DB is required`。此結果未作為成功證據。
2. `a7b7584c843d` / execution `aa21acaa12794038997f0a93f35df1eb`：gateway builtin schedule。Service env與durable ingestion成功，但CLI explicit `deliver` job沒有`origin` metadata，ledger origin為null。此結果只證明gateway env與hook ingestion，不作routing成功證據。
3. `ecca3943fd75` / execution `a7d028fbd79a4e4d9c67a1de34adfd43`：以Hermes公開`cron.jobs.create_job`建立`deliver=origin`及Telegram origin。Gateway builtin schedule完成，Telegram delivery成功，ledger origin read-back如下：
   - platform：`telegram`
   - conversation_id：`8686567559`
   - thread_id：`null`（DM符合預期）
   - outcome：`succeeded`

沒有任何既有production job；closure時`hermes cron list`回報`No scheduled jobs`。

## Dedup read-back

對第三次fixture的相同canonical payload replay：

- Bridge exit：`0`
- Receipt：`duplicate=true`
- Reconciliation runs：before `2` / after `2`
- Outbox：before `1` / after `1`
- Origin event outbox item保持唯一、state `pending`、attempts `0`。

Pending outbox符合目前架構：observer bridge負責durable enqueue，未在本Stage授權啟動額外reconciliation dispatcher或自動remediation。

## Final read-back

- `hermes-bastet.service`：`active/running`
- Production verifier：`applied`
- Config：1個hook、auto-accept false
- Consent：1個exact approval
- SQLite及state permissions：`0600` / `0700`
- Fixture jobs：0
- Fixture script：absent
- Provider/model/credential：未變更
- Backup、DB、agent log及cron execution history保留為audit evidence

## Conclusion

STAGE-005 production rollout gates通過。兩個fixture方法缺陷均被tool evidence攔截並修正；沒有以delivery成功、service active或agent自述單獨宣稱完成。
