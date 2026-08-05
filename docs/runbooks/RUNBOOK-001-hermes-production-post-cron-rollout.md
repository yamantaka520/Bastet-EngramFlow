# Bastet Hermes `post_cron_job` Production Rollout Runbook

Status: readiness-only; execution requires explicit production approval.

## Fixed scope

- Service: `hermes-bastet.service`
- Service owner: `bastet`
- Hermes checkout: `/home/bastet/.hermes/hermes-agent`
- Required pre-deploy Hermes HEAD: `d0c0a6b8fe5ff45bcb3d2ba34e596cca7100ed5a`
- Patch variant: `production-d0c0a6b`
- Patch SHA-256: `af1d421f0b33ee06e14dae9bfca20e4c5490e13c28f78b76dbb9979614cc65dc`
- Wire schema: `hermes.post_cron_job.v1`
- Hook event: `post_cron_job`

Do not continue if the checkout is dirty, `HEAD` differs, the patch verifier does
not report `applicable`, or the service/config ownership differs from the
preflight evidence.

## Proposed production paths

These paths are proposals and are not created by STAGE-004 readiness work:

- Bastet bridge venv: `/home/bastet/.hermes/bastet-engramflow-venv`
- Durable reconciliation DB: `/home/bastet/.hermes/state/bastet-reconciliation.sqlite3`
- Backups: `/home/bastet/.hermes/backups/post-cron-<UTC timestamp>/`

The command registered in the hook must be the venv console script:

```text
/home/bastet/.hermes/bastet-engramflow-venv/bin/bastet-hermes-post-cron
```

## Approval gate

Before any production mutation, record:

1. Approved maintenance window.
2. Approved Bastet-EngramFlow release SHA.
3. Current Hermes `HEAD` and clean status.
4. Current SHA-256 and metadata for `config.yaml` and, if present,
   `shell-hooks-allowlist.json`.
5. Current `systemctl show hermes-bastet.service` state.
6. A named rollback operator.

## Pre-deploy commands (read-only)

Run from the accepted Bastet-EngramFlow release checkout:

```bash
sudo -n -u bastet git -C /home/bastet/.hermes/hermes-agent \
  status --short --branch --untracked-files=no
sudo -n -u bastet git -C /home/bastet/.hermes/hermes-agent rev-parse HEAD
python3 integrations/hermes/verify_patch.py \
  --variant production-d0c0a6b \
  --hermes-tree /home/bastet/.hermes/hermes-agent \
  --expect applicable
systemctl show hermes-bastet.service \
  -p ActiveState -p SubState -p MainPID -p ExecStart -p User --no-pager
```

The verifier may need to run as `bastet` when home-directory traversal prevents
another user from reading the checkout.

## Mutation sequence (not authorized by STAGE-004)

1. Stop `hermes-bastet.service` and verify it is inactive.
2. Copy `config.yaml` and `shell-hooks-allowlist.json` (when present) to the
   timestamped backup directory, preserving mode and ownership.
3. Create the dedicated bridge venv with Python 3.11 and install the exact
   approved Bastet-EngramFlow release. Do not use the host `pip`, which targets
   a different Python version.
4. Create the durable state directory owned by `bastet`, mode `0700`.
5. Apply the exact patch and run the production-source targeted tests before
   committing the source change. Before continuing, require both:

```bash
python3 integrations/hermes/verify_patch.py \
  --variant production-d0c0a6b \
  --hermes-tree /home/bastet/.hermes/hermes-agent \
  --expect applied
sudo -n -u bastet git -C /home/bastet/.hermes/hermes-agent \
  status --short --untracked-files=all
```

   The status output must contain only the paths declared by the selected patch;
   any unrelated path is a stop condition.
6. Add only this config block; leave `hooks_auto_accept` false:

```yaml
hooks:
  post_cron_job:
    - command: /home/bastet/.hermes/bastet-engramflow-venv/bin/bastet-hermes-post-cron
      timeout: 20
```

7. Add `BASTET_RECONCILIATION_DB` to the service environment using a systemd
   drop-in or an existing non-secret env file. Do not place credentials in the
   unit or repository.
8. Approve only the exact event/command pair through Hermes shell-hook consent.
   Do not set global `hooks_auto_accept: true` and do not retain
   `HERMES_ACCEPT_HOOKS=1` in the service environment.
9. Start the service and perform the read-back checks below.

## Post-start read-back

Required evidence before calling deployment successful:

```bash
systemctl is-active hermes-bastet.service
systemctl show hermes-bastet.service -p MainPID -p ExecMainStartTimestamp --no-pager
sudo -n -u bastet git -C /home/bastet/.hermes/hermes-agent status --short --branch
```

Then execute one explicitly named fixture cron job targeted to the original
Telegram conversation/thread. Verify all of the following without printing raw
prompts or credentials:

- Hermes ledger has one terminal execution ID.
- Bastet reconciliation DB has one matching run and one outbox item.
- Replaying the same hook payload does not create a second outbox item.
- The outbox target retains the original Telegram thread ID.
- The gateway log contains no hook exception or delivery regression.
- Existing non-fixture jobs were not triggered by the validation.

## Rollback triggers

Rollback immediately when any occurs:

- service fails to become active;
- hook blocks or changes cron success/failure status;
- duplicate durable outbox items appear for one execution ID;
- original-thread routing is lost;
- config/allowlist consent is broader than the exact hook command;
- unexpected production checkout drift is detected.

## Rollback sequence

1. Stop `hermes-bastet.service`.
2. Revert the dedicated Hermes deployment commit, or reverse-apply the exact
   production variant only after the verifier confirms `applied`.
3. Restore `config.yaml`, `shell-hooks-allowlist.json`, and the systemd drop-in
   from the timestamped backup; run `systemctl daemon-reload` only if a drop-in
   changed.
4. Start `hermes-bastet.service`.
5. Verify active state, original Hermes `HEAD`/source state, config checksums,
   and a normal non-hook health probe.
6. Preserve the failed reconciliation DB and logs for audit; do not delete them
   during rollback.

Removing the dedicated venv/state directory is a later cleanup decision, not
part of emergency rollback.
