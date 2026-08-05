---
id: PLAN-010
title: Source-pinned Hermes context consumer production artifact plan
type: plan
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-009
related_adrs:
  - ADR-0004
  - ADR-0005
related_evidence:
  - EVID-011
---

# PLAN-010 — Source-pinned Hermes Context Consumer Production Artifacts

## Goal

在不變更production的前提下，將Hermes exact-routing compatibility patch與fail-closed consumer plugin轉為可digest、可重現、可獨立審查與可rollback的deployment inputs。

## Workstreams

### 1. Read-only live preflight

- 核對`hermes-bastet.service` owner、ExecStart、state與delivery env缺失狀態。
- 核對live Hermes HEAD、既有post-cron patch state與dirty-path allowlist。
- 核對`pre_llm_call` callsite及`_chat_id`/`_thread_id`來源。
- 以SQLite `mode=ro`讀取source outbox state；不得呼叫delivery queue constructor。
- 核對state filesystem為local supported type與private DB directory。

### 2. TDD plugin artifact

- 先建立缺artifact RED tests。
- 實作`plugin.yaml`與`register(ctx)`。
- 缺環境、相對/不存在/不安全/未初始化DB時fail closed且零hook。
- 使用真實Hermes`PluginManager`載入artifact並執行wrong/exact route。

### 3. Source-pinned compatibility patch

- 從exact base commit建立isolated clone。
- patch只在現有`pre_llm_call` invocation增加conversation/thread kwargs。
- 建立unpatched RED與patched GREEN execution tests。
- 固定patch、plugin及test SHA-256與changed-path manifest。

### 4. Verification and governance

- 提供唯一canonical source-pinned runner，避免ambient/root pytest誤收集。
- 執行full repository static/docs/test gates。
- 獨立review source, plugin, manifest, tests及production boundary。
- 完成evidence/review/status/traceability與approval pack更新。
- commit、push及remote read-back。

## Stop Conditions

- Hermes HEAD不是manifest固定commit。
- Live dirty paths超出既有bridge prerequisite或approved context patch。
- Delivery path是NFS/remote/unknown filesystem。
- Production source outbox/delivery queue出現未解釋lease、sending或ambiguous state。
- Plugin validation會建立/migration不存在的DB。
- Patch改到allowlist外路徑或使用sender fallback。
- 未取得明確production approver、window、backup/rollback operator、existing item disposition與canary target。

## Rollback Boundary

本Plan不執行production mutation，因此repository工作只需Git revert。未來deployment rollback必須先停dispatcher，再停止consumer/Hermes，將`sending`視為`ambiguous`，恢復verified source/config/plugin/release備份並隔離delivery DB；不得刪除或自動重送ambiguous row。
