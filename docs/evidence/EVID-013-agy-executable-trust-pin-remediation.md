---
id: EVID-013
title: AGY executable trust-pin remediation evidence
type: evidence
status: accepted
owner: engineering
created: 2026-08-06
updated: 2026-08-06
related_goals:
  - GOAL-001
related_stages:
  - STAGE-009
related_plans:
  - PLAN-010
related_adrs:
  - ADR-0005
---

# EVID-013 — AGY Executable Trust-Pin Remediation

## Scope and authorization

- Scope was limited to the Bastet primary-provider prerequisite: read-only binary disposition, owner-private backup, one `AGY_CLI_SHA256` update, `daemon-reload`, `hermes-bastet.service` restart, identity/transport/functional probes and necessary rollback.
- Explicit approval was recorded for the complete AGY remediation, one representative functional probe with possible model usage and necessary rollback.
- This authorization did **not** include the STAGE-009 compatibility patch, consumer plugin, dedicated venv, delivery DB, dispatcher, source/sink replay or another production canary.
- Owner-private approval artifact: `/home/bastet/.hermes/backups/agy-trust-repin/20260806_202055/approval.txt`; SHA-256 `88510a40d6055917c7ae08f3f66c172e6e7a975adf93cced30ee8cb86f80e147`.

## Read-only executable disposition

- Live executable: `/home/bastet/.local/bin/agy`, owner `bastet:bastet`, mode `0755`, size `193835456`, mtime `2026-08-03 12:00:20 CST`.
- Live SHA-256: `4217db798fd514cedce4e315013daea471a1a67666ab91547b2ad0dbee167a71`.
- Previous service pin: `edec0312023c2e062e2080c8989ff86a74342c0fde6bd7e3e4cfb6528e795753`.
- No regular-file copy with the previous digest was found under `/home/bastet`; restoration of the previously pinned binary therefore was not represented as available.
- The official installer source is `https://antigravity.google/cli/install.sh`; it resolves the Linux AMD64 manifest from the Google-hosted Antigravity release service and verifies the release archive with SHA-512.
- Official `linux_amd64` manifest version: `1.1.10`; published archive SHA-512: `e64d4e58ede0f8440f2b3dc021f9d6d36b05f5c2f74d5a9215c1f11b20d536c8c2e020f4ce5257aa67e940e94c94d5a16d3aa6461cda18ee7f3e74d3a20ca1ac`.
- A temporary download of the official release archive matched that SHA-512 exactly. The archive contained one executable, `antigravity`, mode `0755`, size `193835456`; its extracted SHA-256 was exactly `4217db798fd514cedce4e315013daea471a1a67666ab91547b2ad0dbee167a71`.
- `--version` was executed only against a temporary copied executable under an empty HOME, `nobody` identity and network namespace. It returned `1.1.10`; the copy and live executable hashes remained unchanged and the sandbox created no files.
- Disposition: the live executable is byte-identical to the checksum-verified official `1.1.10` release. The stale pin resulted from the CLI's documented background self-update behavior, not evidence of an unknown binary.

## Backup and mutation

- Backup root: `/home/bastet/.hermes/backups/agy-trust-repin/20260806_202055`, owner-private mode `0700`.
- Pre-change drop-in SHA-256: `b3cabdfbdab4054bee1fabdbf8a4283733b75f5cb12315fcb210199c8b0b8324`.
- The only persistent configuration change replaced the exact prior `AGY_CLI_SHA256` line with `4217db798fd514cedce4e315013daea471a1a67666ab91547b2ad0dbee167a71` in `/etc/systemd/system/hermes-bastet.service.d/agy-adapter.conf`.
- Current drop-in SHA-256: `99d8e1358e0d6bebdf598432461ce5f5210c2c1cd5e2777172591d291d3b3257`.
- Update was written with a same-directory temporary file, file/parent fsync and atomic replace while preserving root ownership and mode `0644`.

## Harness failures and rollback behavior

- One pre-change attempt stopped before mutation because the owner-private backup directory prevented caller-side glob expansion.
- One functional-probe attempt stopped before model execution because caller-side redirection could not create the owner-private evidence file; the rollback trap restored the prior drop-in and restarted the service.
- A second functional-probe attempt stopped before AGY execution because the CLI inherited `/home/neo` as cwd and `bastet` could not traverse `/home/neo/.git`; the rollback trap again restored the prior drop-in and restarted the service.
- The final probe used a direct Python `subprocess` as `bastet`, fixed cwd `/home/bastet/.hermes/agy-adapter-workdir`, no nested privileged shell, and the production AGY environment. These harness failures did not claim AGY failures and did not alter queue state.

## Final verified gates

- Effective systemd pin equals the live SHA-256: PASS.
- Adapter identity: `ok=true`, `hash_pinned=true`, `hash_ok=true`, `version=1.1.10`, `version_supported=true`, `stdin_transport=true`, trusted owner and safe mode.
- Post-restart authoritative transport evidence: `gateway.log` `Connected to Telegram (polling mode)` at `2026-08-06 20:24:38 CST`.
- Representative Hermes main-route probe used provider `custom`, model `gemini-3.6-flash-high` and the `terminal` tool schema. It exited `0` and its final non-empty line was exactly `AGY_FUNCTIONAL_GATE_OK`.
- Functional probe evidence SHA-256: `6d6c17fe5f731b0d90e6723808b11a740808919aaa78b279ec25e502efd9863c`.
- Final service read-back: `active/running`, `MainPID=2488484`, active since `2026-08-06 20:24:24 CST`.
- Live executable still matched the approved SHA-256 after all probes.

## STAGE-009 boundary and queue read-back

- Context consumer plugin, dedicated venv, consumer drop-in and live delivery DB remain absent; the exact-routing compatibility patch remains rolled back.
- Source outbox remains `delivered/attempts=1` with leases cleared.
- Quarantined sink remains `pending/attempts=0` with no prepared, sending, delivered or ambiguous timestamp.
- Both source and quarantine SQLite integrity checks returned `ok`.
- No row was reset, replayed, claimed, merged or dispatched during this remediation.

## Repository validation

- Isolated CPython 3.11.15 test venv under `/tmp`; project source was loaded with `PYTHONPATH=src` so the NAS checkout did not receive build metadata.
- Focused dispatcher/plugin/consumer/artifact-verifier/documentation-governance suite: `33 passed in 1.03s`.
- `git diff --check`: PASS.
- `python -m compileall -q src tests`: PASS.
- Pytest emitted one non-gating cache warning because the NAS filesystem rejected creation of `.pytest_cache`; collection and all 33 test results completed successfully.

## Verdict

- AGY executable origin/version/digest disposition: VERIFIED.
- AGY trust-pin remediation: PASS.
- Bastet primary-route functional prerequisite: PASS.
- Previous AGY High blocker: CLOSED.
- STAGE-009 production context-consumer enablement: still WITHHELD pending a new maintenance window, explicit per-item disposition and fresh rollout/canary/rollback authorization.
