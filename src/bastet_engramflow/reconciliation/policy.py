"""Policy evaluation for scheduled execution reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import (
    ActionClass,
    ConversationContextEvent,
    FindingSeverity,
    ReconciliationDecision,
    RemediationDisposition,
    RemediationProposal,
    ScheduledRunEnvelope,
)


@dataclass(frozen=True, slots=True)
class ReconciliationPolicy:
    """Boundaries for remediation eligibility; it performs no execution."""

    max_auto_remediation_depth: int = 1
    auto_action_classes: frozenset[ActionClass] = field(
        default_factory=lambda: frozenset({ActionClass.READ_ONLY})
    )

    def __post_init__(self) -> None:
        if self.max_auto_remediation_depth < 0:
            raise ValueError("max_auto_remediation_depth must not be negative")

    def evaluate(self, run: ScheduledRunEnvelope) -> ReconciliationDecision:
        event = ConversationContextEvent(
            event_id=f"scheduled:{run.schedule_id}:{run.run_id}",
            schedule_id=run.schedule_id,
            run_id=run.run_id,
            target=run.origin,
            occurred_at=run.occurred_at,
            outcome=run.outcome,
            summary=run.summary,
            findings=run.findings,
            artifacts=run.artifacts,
        )
        if not run.findings:
            return ReconciliationDecision(
                event=event,
                disposition=RemediationDisposition.NONE,
                proposal=None,
            )

        reasons: set[str] = set()
        if any(not finding.retryable for finding in run.findings):
            reasons.add("retryable")
        if any(
            finding.severity is FindingSeverity.CRITICAL for finding in run.findings
        ):
            reasons.add("critical")
        if any(
            finding.action_class not in self.auto_action_classes
            for finding in run.findings
        ):
            reasons.add("action_class")
        if run.remediation_idempotency_key is None:
            reasons.add("idempotency")
        if run.continuation_depth >= self.max_auto_remediation_depth:
            reasons.add("depth")

        disposition = (
            RemediationDisposition.APPROVAL_REQUIRED
            if reasons
            else RemediationDisposition.AUTO_ELIGIBLE
        )
        proposal = RemediationProposal(
            proposal_id=f"remediate:{run.schedule_id}:{run.run_id}",
            schedule_id=run.schedule_id,
            source_run_id=run.run_id,
            why_now=(
                f"Scheduled run {run.run_id} reported {len(run.findings)} finding(s)"
            ),
            findings=run.findings,
            idempotency_key=run.remediation_idempotency_key,
            continuation_depth=run.continuation_depth + 1,
            requires_approval=(disposition is RemediationDisposition.APPROVAL_REQUIRED),
        )
        return ReconciliationDecision(
            event=event,
            disposition=disposition,
            proposal=proposal,
            reasons=frozenset(reasons),
            problem_resolved=False,
        )
