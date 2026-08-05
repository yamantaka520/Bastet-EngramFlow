# Hermes `post_cron_job` Integration

This directory contains source-pinned integration artifacts. It does **not**
automatically modify a running Hermes installation.

## Compatibility variants

### Baseline fixture

- Hermes commit: `1072c0725115e9be0491ca4cb0d965b9f5f59874`
- Patch: `patches/1072c0725-post-cron-job-hook.patch`
- SHA-256: `2fa36a110d7dcf9a3fb5846ede59c95a5162edbea6f4c792b7026079a7d30c5b`

### Bastet production source baseline

- Hermes commit: `d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`
- Patch: `patches/d0c0a6b-post-cron-job-hook.patch`
- SHA-256: `af1d421f0b33ee06e14dae9bfca20e4c5490e13c28f78b76dbb9979614cc65dc`

Both variants use wire schema `hermes.post_cron_job.v1`. Refuse deployment
when the source commit or patch digest differs.

The production-source variant attaches to the shared `run_one_job()` lifecycle,
so built-in and Chronos scheduler providers use the same observer path. It uses
Hermes' durable execution ID as `run_id` and preserves the interrupted-run
ledger semantics introduced by that source version.

## Isolated verification

The verifier selects the exact variant from the target checkout's `HEAD` and
checks both SHA-256 and apply/reverse-apply state:

```bash
python3 integrations/hermes/verify_patch.py \
  --hermes-tree /path/to/hermes \
  --expect applicable
```

Optionally lock the expected variant explicitly:

```bash
python3 integrations/hermes/verify_patch.py \
  --variant production-d0c0a6b \
  --hermes-tree /path/to/hermes \
  --expect applicable
```

Apply only to an isolated clone/worktree first. The runner refuses an unpatched
or wrong-HEAD target, forces the target checkout to the front of `PYTHONPATH`,
and runs the manifest-selected target tests plus the external real shell bridge
E2E:

```bash
python3 integrations/hermes/run_variant_tests.py \
  --variant production-d0c0a6b \
  --hermes-tree /path/to/patched-hermes
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

- Each actual run emits at most once after its ledger terminalization; this is
  not a global exactly-once guarantee.
- Claim-rejected attempts do not emit because no job body ran.
- Hook exceptions fail open for the existing Hermes cron path.
- The payload excludes raw prompts, redacts/bounds result text, and exposes only
  a sanitized output artifact basename rather than a host-local absolute path.
- The bridge rejects unknown schema fields and validates identity before durable
  enqueue.
- The baseline variant generates a run UUID. The production-source variant uses
  the durable Hermes execution ID. A scheduler re-execution still receives a new
  execution ID; replaying the same emitted payload is deduplicated.
- Delivery remains at-least-once; sinks deduplicate the stable IDs carried by
  each persisted payload, not a cross-reexecution business identity.
- These artifacts do not restart services or alter production configuration.
