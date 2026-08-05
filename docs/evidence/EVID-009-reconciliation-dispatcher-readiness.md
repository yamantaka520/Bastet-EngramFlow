---
id: EVID-009
title: Fail-closed reconciliation dispatcher readiness evidence
type: evidence
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-007
related_plans:
  - PLAN-008
related_adrs:
  - ADR-0004
  - ADR-0005
---

# EVID-009 — Fail-closed Reconciliation Dispatcher Readiness

## Environment

- Repository: `/mnt/nas/Hermes-Gitlab/Bastet-EngramFlow`
- Branch: `feat/hermes-production-reconciliation-hook`
- Starting commit: `d18b561191593a6103403b43181ef14908dfb1b9`
- Evidence timestamp: 2026-08-05 18:21:11 CST（UTC+8）
- Production mutation: none

## Hermes API Discovery

Hermes source read-back確認outbound `send_message`最終直接呼叫live `adapter.send()`；未找到可重用的durable/idempotent outbound queue。直接Telegram/platform delivery無event-id原生idempotency，不能滿足既有`ConversationInbox` contract。因此本Stage採Bastet-owned durable Hermes context/proposal queue，保留stable `HermesConversationIngress` seam，不直接呼叫platform API。

## RED

Initial focused command：

```bash
PYTHONPATH=src:. python3 -m unittest tests.test_reconciliation_dispatcher -v
```

Result: exit `1`，ImportError指出`SQLiteHermesDeliveryQueue`尚不存在，符合預期RED。

Independent review後新增兩項regression：

- hardlink alias可繞過原先純resolved-path comparison；RED實際造成SQLite `disk I/O error`。
- generic sink exception文字被CLI回顯；RED stderr包含測試conversation/thread identifier與summary。

## GREEN Focused Gate

Implemented artifacts：

- `src/bastet_engramflow/reconciliation/delivery_queue.py`
- `src/bastet_engramflow/reconciliation/dispatch_cli.py`
- `tests/test_reconciliation_dispatcher.py`
- Public exports及`bastet-reconciliation-dispatch`console script。

Final focused command：

```bash
python3 -m compileall -q \
  src/bastet_engramflow/reconciliation/delivery_queue.py \
  tests/test_reconciliation_dispatcher.py
ruff format --check <dispatcher files>
ruff check <dispatcher files>
PYTHONPATH=src:. python3 -m unittest tests.test_reconciliation_dispatcher -v
```

Result: exit `0`；3 files formatted；lint PASS；10 tests PASS。

Covered assertions：

- Sink commit後source ack前崩潰重播只保留一筆context row及同一receipt。
- 同event ID不同payload fail closed。
- Proposal replay stable receipt且只保留一筆row。
- Oversized sink payload在write前拒絕。
- 缺enable flag不開啟或建立delivery DB，source state不變。
- Enabled temp-DB dispatch每次最多一項，event後proposal，source最終delivered。
- Missing source不建立source或delivery DB。
- Same path與hardlink same-inode alias均在mutation前拒絕。
- Success aggregate與failure stderr不含conversation/thread ID、summary或exception message。

## Review Round 1

Fresh-context review指出：

- Medium/High boundary：resolved-path equality不能阻擋hardlink same inode。
- Medium：catch-all stderr回顯`str(exc)`與redaction claim不一致。
- 測試缺口：alias與failure stderr redaction。

修復後加入`Path.samefile()`/regular-file preflight，並將runtime failure改為固定redacted訊息。兩項regression及完整focused suite均GREEN。

## Formatting Incident and Recovery

NAS root-squash拒絕terminal formatter直接寫入，因此先在`/tmp`格式化副本。第一次file API回填誤用了帶行號展示內容，lint立即偵測兩檔SyntaxError；未commit、未push、未觸碰production。取得明確修復授權後，以raw `Path.read_text()`回填同一formatter副本，兩檔lint恢復OK，compile/ruff/10-test read-back全部通過。此事件不被隱藏或誤報為無故障流程。

## Production Boundary Read-back

本Stage沒有對production DB執行dispatcher，沒有建立production delivery DB，沒有claim/ack/fail pending item，沒有修改或重啟Hermes service，也沒有呼叫Telegram/platform sink。Production enablement仍待獨立approval pack。

## Closure

- Full repository gate：40 files formatted、Ruff lint PASS、81 tests PASS、documentation governance PASS、compileall PASS、diff check PASS。
- [REVIEW-009](../reviews/REVIEW-009-stage-007-reconciliation-dispatcher-readiness.md)：final repository-readiness ACCEPT，open High/Medium/Low均0；production approval明確WITHHELD。
- Production boundary read-back：沒有production dispatcher execution、delivery DB creation、outbox mutation、service/config mutation或platform call。
- Commit、push與remote SHA read-back於publication closure執行並回報。
