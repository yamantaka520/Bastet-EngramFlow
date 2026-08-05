"""Coordinator for idempotent scheduled-run reconciliation."""

from __future__ import annotations

from dataclasses import replace
from threading import RLock

from .models import ReconciliationReceipt, ScheduledRunEnvelope
from .policy import ReconciliationPolicy
from .ports import ConversationInbox, RemediationProposalSink


class ReconciliationCoordinator:
    """Process-local coordinator; production also needs a durable ledger/outbox."""

    def __init__(
        self,
        *,
        inbox: ConversationInbox,
        proposals: RemediationProposalSink,
        policy: ReconciliationPolicy | None = None,
    ) -> None:
        self._inbox = inbox
        self._proposals = proposals
        self._policy = policy or ReconciliationPolicy()
        self._committed: dict[tuple[str, str], ReconciliationReceipt] = {}
        self._lock = RLock()

    def process(self, run: ScheduledRunEnvelope) -> ReconciliationReceipt:
        """Reconcile one run and commit its key only after required sinks succeed."""
        with self._lock:
            existing = self._committed.get(run.run_key)
            if existing is not None:
                return replace(existing, duplicate=True)

            decision = self._policy.evaluate(run)
            delivery_receipt = None
            if decision.event.target is not None:
                delivery_receipt = self._inbox.publish(decision.event)

            proposal_receipt = None
            if decision.proposal is not None:
                proposal_receipt = self._proposals.submit(decision.proposal)

            receipt = ReconciliationReceipt(
                decision=decision,
                delivery_receipt=delivery_receipt,
                proposal_receipt=proposal_receipt,
            )
            self._committed[run.run_key] = receipt
            return receipt
