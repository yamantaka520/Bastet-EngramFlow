# Hermes `post_cron_job` Integration

This directory contains a source-pinned integration artifact. It does **not**
automatically modify a running Hermes installation.

## Compatibility baseline

- Hermes commit: `1072c0725115e9be0491ca4cb0d965b9f5f59874`
- Wire schema: `hermes.post_cron_job.v1`
- Patch: `patches/1072c0725-post-cron-job-hook.patch`
- SHA-256: `2fa36a110d7dcf9a3fb5846ede59c95a5162edbea6f4c792b7026079a7d30c5b`

Refuse deployment when the source commit or patch digest differs.

## Isolated verification

```bash
test "$(git -C /path/to/hermes rev-parse HEAD)" = \
  "1072c0725115e9be0491ca4cb0d965b9f5f59874"
sha256sum -c <<'EOF'
2fa36a110d7dcf9a3fb5846ede59c95a5162edbea6f4c792b7026079a7d30c5b  integrations/hermes/patches/1072c0725-post-cron-job-hook.patch
EOF
git -C /path/to/hermes apply --check \
  /path/to/Bastet-EngramFlow/integrations/hermes/patches/1072c0725-post-cron-job-hook.patch
```

Apply only to an isolated worktree first. Copy the fixture tests into that
worktree and run:

```bash
python3 -m pytest \
  tests/cron/test_post_cron_hook.py \
  tests/cron/test_scheduler.py \
  tests/agent/test_shell_hooks.py \
  tests/agent/test_shell_hooks_consent.py -q
BASTET_REPO_ROOT=/path/to/Bastet-EngramFlow \
  python3 -m pytest tests/cron/test_shell_bridge_e2e.py -q
```

## Bridge installation seam

Install Bastet-EngramFlow into a dedicated virtual environment and configure
Hermes' existing allowlisted shell hook:

```yaml
hooks:
  post_cron_job:
    - command: /path/to/bastet-venv/bin/bastet-hermes-post-cron
      timeout: 20
```

The hook subprocess requires:

```bash
BASTET_RECONCILIATION_DB=/durable/local/path/reconciliation.sqlite3
```

Approve the exact event/command pair through Hermes' normal hook consent flow.
Do not enable `hooks_auto_accept` globally merely to deploy this integration.
The committed E2E fixture uses the equivalent `python -m` entry point so it can
run from source without installing a console script; production uses the
packaged `bastet-hermes-post-cron` command shown above.

## Safety boundary

- Each `_process_job()` path emits at most once and only after `mark_job_run()`;
  this is not a global exactly-once guarantee.
- Hook exceptions fail open for the existing Hermes cron path.
- The payload excludes raw prompts, redacts/bounds result text, and exposes only
  a sanitized output artifact basename rather than a host-local absolute path.
- The bridge rejects unknown schema fields and validates identity before durable
  enqueue.
- The generated UUID is stable only within one emitted payload. Re-executing a
  job creates a new run identity; replaying the same payload is deduplicated.
- Delivery remains at-least-once; sinks deduplicate the stable IDs carried by
  each persisted payload, not a cross-reexecution business identity.
- This artifact does not restart services or alter production configuration.
