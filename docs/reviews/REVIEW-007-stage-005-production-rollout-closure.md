---
id: REVIEW-007
title: STAGE-005 Bastet Hermes production rollout closure review
type: review
status: accepted
owner: independent-review
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-005
related_plans:
  - PLAN-006
related_evidence:
  - EVID-007
---

# REVIEW-007：STAGE-005 Production Rollout Closure Review

## Scope

Fresh-context reviewer以read-only方式檢查：

- closure working-tree diff與EVID-007；
- live `hermes-bastet.service`、systemd unit/drop-in；
- production Hermes HEAD、manifest-owned changed paths及patch verifier；
- hook config、exact consent cardinality及permissions；
- reconciliation SQLite schema/counts與pending outbox boundary。

Reviewer未修改repository或production。

## Independent read-back

- Bastet-EngramFlow release HEAD：`5e2d29a12f60d84c76ca50148ab02a36b798c4bb`。
- Production Hermes HEAD：`d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`。
- Verifier：variant `production-d0c0a6b`、state `applied`。
- Live source dirty paths只含manifest的三個paths。
- Service：`active/running`，review時MainPID `2371863`。
- Config：`hooks_auto_accept=false`、1個`post_cron_job` hook、exact bridge command、timeout `30`。
- Consent：1個exact event/command pair。
- Permissions：config/allowlist/SQLite `0600`、state directory `0700`、drop-in `0644 root:root`。
- DB：reconciliation runs `2`、outbox `1`、pending outbox `1`。
- Pending outbox只代表durable enqueue；本Stage未宣稱dispatcher delivery或remediation完成。

## Findings

### High

- 無。

### Medium M-007-01：Fixture boundary overrun

批准邊界是1個fixture加1次replay；實際有3次fixture attempts：CLI direct、gateway explicit-deliver/no-origin、gateway origin fixture。前兩次分別揭露systemd env與origin metadata差異，但仍屬批准數量外的治理例外。

**Disposition：closed as documented governance exception。**

- 三次皆為相同固定stdout、no-agent、無tools/LLM/network。
- EVID-007逐次記錄各attempt能與不能證明的事項，沒有把partial result冒充成功。
- Jobs與fixture script均已清除；沒有既有production job被觸發。
- 使用者收到完整例外與影響報告後指示繼續推進closure。
- RUNBOOK-001與production-rollout procedural reference已加入：若approved fixture被diagnostic消耗而需要額外外部delivery，必須先取得renewed approval。
- 本結案不再執行任何fixture。

### Medium M-007-02：Manifest-owned uncommitted production patch

Production Hermes保留base HEAD加local manifest-owned patch，而不是immutable deployment commit/tag。這是目前source-pinned rollout設計，但未來upstream maintenance較容易擾動。

**Disposition：closed as controlled residual operational risk。**

- Base SHA、patch SHA-256、variant與changed-path manifest均已固定。
- Forward/reverse verifier、timestamped source/config backup及rollback trap均有實測證據。
- Production checkout changed paths只限manifest；PROJECT_STATUS保留此upgrade risk。
- 未經另一次production approval，不把local patch擅自commit或改寫production branch history。
- 後續upgrade前必須先做verifier/changed-path preflight；immutable deployment commit/tag須另立change approval。

## Claim review

- Production claims有service、source、config、consent、DB及fixture read-back支持，不依賴agent自述。
- Initial stop-state failure及兩次partial fixture attempts均已揭露。
- Rollback trap已實際恢復service/source，RUNBOOK已納入systemd stop quirk。
- Telegram delivery、origin propagation與dedup分別有真實gateway fixture及DB證據。
- Outbox dispatcher/remediation未啟用，也未被錯誤宣稱完成。

## Final decision

- Open High findings：`0`
- Open Medium findings：`0`
- Accepted documented governance exceptions：`1`
- Accepted controlled residual operational risks：`1`
- Recommendation：`ACCEPT`

STAGE-005 acceptance evidence與repository gate均已完成；publication closure須在本文件commit、push並完成remote SHA read-back後才可宣告完成。
