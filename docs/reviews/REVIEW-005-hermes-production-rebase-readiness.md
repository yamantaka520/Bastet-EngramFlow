---
id: REVIEW-005
title: Hermes production SHA rebase readiness review
type: review
status: accepted
owner: verification
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
related_evidence:
  - EVID-005
---

# REVIEW-005: Hermes Production SHA Rebase Readiness

## Scope

Independent review covered the uncommitted STAGE-004 production-SHA artifact,
manifest/verifier, hook lifecycle semantics, fixture reproducibility, and
production rollout/rollback runbook.

## Initial findings

### High: production fixture was not hermetic

Running the stored production fixture directly from the Bastet repository could
import an ambient Hermes installation instead of the selected target checkout.
This made that invocation unsuitable as reproducible compatibility evidence.

Resolution:

- Added `run_variant_tests.py`.
- Runner verifies exact `HEAD` and `applied` state before tests.
- Runner places the target Hermes checkout first in `PYTHONPATH` and uses it as
  the subprocess working directory.
- Manifest declares target-tree tests per variant.
- Exact runner execution returned `358 PASS`.

Status: closed.

### Medium: runbook lacked a positive post-apply verifier gate

Resolution:

- Added explicit `--expect applied` verification after patch application.
- Added exact changed-path status review and stop-on-unrelated-path rule.

Status: closed.

### Low: abbreviated review-base reference was not resolvable in one reviewer context

Resolution:

- Closure evidence uses full source and artifact SHAs rather than relying on an
  abbreviated review-base reference.

Status: closed.

## Final independent read-back

The follow-up reviewer inspected the runner, manifest, verifier, README,
production runbook, target checkout HEAD, applied path set, and target tests.

Final findings:

- High: `0`
- Medium: `0`
- Unresolved blockers: `0`

## Reviewer conclusion

STAGE-004 may be accepted as **production rollout readiness**. The code and
artifact are not approved as already deployed, and the runbook's explicit
production mutation gate remains binding.
