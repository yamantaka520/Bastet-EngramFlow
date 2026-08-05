---
id: REVIEW-004
title: Hermes post-cron hook 與 durable bridge 獨立審查
type: review
status: accepted
owner: independent-reviewer
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
related_evidence:
  - EVID-004
---

# REVIEW-004：Hermes post-cron hook 與 durable bridge 獨立審查

## Scope

- Pinned Hermes scheduler/plugin patch與source fixture。
- Bastet strict shell bridge、CLI、durable receipt/error bounds。
- Scheduler→shell subprocess→SQLite E2E。
- Artifact manifest、digest、compatibility與安全邊界文件。

## Round 1 Findings

兩位獨立reviewer分別審查upstream patch與Bastet bridge。

- High 1：absolute `output_path`可能揭露host structure，README安全聲明過強。
- Medium 1：single-fire用語可能被誤讀為全域exactly-once。
- Medium 2：failure、delivery error與exception payload測試不足。
- Medium 3：E2E直接呼叫hook，未覆蓋patched scheduler `tick()`。
- Medium 4：UUID不具跨re-execution穩定business identity，文件表述過強。
- Low 1：unknown fields被silent ignore。
- Low 2：README與manifest baseline未由test鎖定。

## Remediation

1. Upstream與bridge雙層將`output_path`收斂為sanitized basename；新增path/secret regression。
2. 文件改為每個`_process_job()` path at-most-once，明確排除global exactly-once。
3. 補runner exception、delivery error、soft failure、hook fail-open fixtures。
4. 新增patched scheduler `tick()`→Hermes shell subprocess→Bastet CLI→SQLite真E2E。
5. 文件明確區分單一payload run UUID、same-payload replay與跨re-execution identity。
6. Bridge拒絕unknown wire/payload/origin fields；允許known telemetry field。
7. Artifact unit test比對patch digest、base commit、wire schema與README manifest內容。

## Final Read-back

Fresh pinned worktree重新apply最終artifact後：

- Clean apply/syntax/diff：PASS。
- Hermes focused regression與E2E：211 PASS。
- Bastet full gate：63 PASS。
- High：0。
- Medium：0。
- Low residual：production rollout與真實Telegram API delivery尚未執行，維持明確out-of-scope。

## Decision

`accepted`。接受範圍為source-pinned非侵入patch artifact、strict durable bridge與isolated integration evidence；不代表production已部署，不包含exactly-once、跨重跑business identity、多主機HA或自動remediation執行。
