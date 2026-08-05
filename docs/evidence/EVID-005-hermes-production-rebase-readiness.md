---
id: EVID-005
title: Hermes production SHA rebase and isolated readiness evidence
type: evidence
status: accepted
owner: engineering
created: 2026-08-05
updated: 2026-08-05
related_goals:
  - GOAL-001
related_stages:
  - STAGE-004
related_plans:
  - PLAN-005
related_adrs:
  - ADR-0005
---

# EVID-005: Hermes Production SHA Rebase and Isolated Readiness

## Accepted claim

The source-pinned `post_cron_job` integration has been rebased to the exact
Bastet production Hermes source commit and is reproducibly applicable/testable
in an isolated clone. The production checkout, config, allowlist, and service
were not modified.

This evidence accepts rollout readiness only. It does not accept or claim a
production deployment.

## Production discovery

Read-only inspection on 2026-08-05 established:

- Service: `hermes-bastet.service`, active/running.
- Service user: `bastet`.
- Checkout: `/home/bastet/.hermes/hermes-agent`.
- Branch: `feat/agy-cli-oauth-stdin-hardening`.
- HEAD: `d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`.
- Tracked source state: clean.
- Existing config had no `hooks`, no `hooks_auto_accept`, and no shell hook
  allowlist file.
- The STAGE-003 baseline patch did not apply to this newer source. Both
  scheduler and plugin hunks rejected, so direct deployment was refused.

## Rebased artifact

- Variant: `production-d0c0a6b`.
- Patch: `integrations/hermes/patches/d0c0a6b-post-cron-job-hook.patch`.
- SHA-256: `af1d421f0b33ee06e14dae9bfca20e4c5490e13c28f78b76dbb9979614cc65dc`.
- Wire schema: `hermes.post_cron_job.v1`.
- Hook seam: shared `run_one_job()` lifecycle used by built-in and Chronos
  scheduler providers.
- Run identity: Hermes durable `execution_id`.
- Interrupted runs preserve the existing no-double-mark behavior and still
  produce one terminal observer event.
- Claim-rejected dispatches do not emit because the job body did not run.

The multi-variant verifier auto-selects by exact `HEAD`, checks the manifest
SHA-256, and requires exactly one of apply or reverse-apply checks to pass.

## Verification results

### Artifact contracts and patch states

- Multi-variant artifact contract tests: `5 PASS`.
- Baseline `1072c0725`: `applicable` verifier PASS.
- Baseline patched tree: `applied` verifier PASS.
- Production `d0c0a6b`: `applicable` verifier PASS.
- Production artifact-applied tree: `applied` verifier PASS.
- Applied production source `git diff --check`: PASS.

### Exact production-variant tests

The hermetic runner first verified the `applied` state, forced the selected
Hermes checkout to the front of `PYTHONPATH`, and ran target-tree tests plus the
external real shell subprocess bridge:

```text
python3 integrations/hermes/run_variant_tests.py \
  --variant production-d0c0a6b \
  --hermes-tree /tmp/hermes-prod-clean-d0c0a6b
```

Result: `358 PASS`, `7 warnings`, 19.95 seconds.

Coverage includes:

- success, execution failure, delivery failure, soft failure;
- hook callback failure/fail-open;
- durable execution ID propagation;
- interrupted-run no-double-mark behavior;
- built-in tick propagation into shared `run_one_job()`;
- execution ledger, scheduler routing, shell hook and consent regression;
- real shell subprocess into Bastet CLI/SQLite;
- replay deduplication and original Telegram thread preservation.

Warnings were pre-existing dependency deprecations and one known unawaited
platform coroutine warning in scheduler/shell-hook tests.

### Bastet repository gate

- Ruff format: PASS (`34 files already formatted`).
- Ruff lint: PASS.
- Unit/integration tests: `63 PASS`.
- Documentation governance: PASS.
- Compileall: PASS.

### Upstream full-suite observation

A complete upstream Hermes pytest run was attempted in the isolated patched
clone. The tracked process eventually reported exit code `0` after 1178 seconds,
but its retained output had no usable terminal pytest summary and contained
repeated background logger `FileNotFoundError` traces after temporary
`HERMES_HOME` directories were removed. Because the output is not a clean,
self-describing pytest result, it is recorded as a non-gating observation rather
than claimed as a clean full-suite PASS.

Production was not affected. The accepted release gate is the manifest-scoped,
hermetic 358-test suite covering all modified lifecycle and shell-hook seams.

## Rollout controls

`RUNBOOK-001` fixes the production service/user/path/HEAD/patch digest and
requires:

- explicit maintenance-window and rollback approval;
- config and allowlist backups;
- exact post-apply verifier read-back;
- exact changed-path inspection;
- dedicated Python 3.11 venv and durable database path;
- no global hook auto-accept;
- service/start, ledger, replay, thread-target, and log read-back;
- source/config/allowlist rollback while preserving evidence.

## Acceptance boundary

Accepted:

- production SHA reconciliation;
- source-pinned artifact and hermetic test runner;
- isolated compatibility and shell bridge validation;
- reviewed production rollout/rollback runbook.

Not accepted or executed:

- production patch application;
- production config/allowlist change;
- venv/database creation;
- service stop/restart;
- real production Telegram delivery.
