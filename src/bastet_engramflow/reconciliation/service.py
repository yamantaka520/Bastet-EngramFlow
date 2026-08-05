"""Durable reconciliation enqueue and at-least-once dispatch service."""

from __future__ import annotations

from dataclasses import dataclass

from .durable import DurableEnqueueReceipt, OutboxKind, SQLiteReconciliationStore
from .models import ScheduledRunEnvelope
from .policy import ReconciliationPolicy
from .ports import ConversationInbox, RemediationProposalSink
from .serde import decode_event, decode_proposal


@dataclass(frozen=True, slots=True)
class DispatchReceipt:
    item_id: str
    kind: OutboxKind
    sink_receipt: str


class DurableReconciliationService:
    """Persist decisions first, then dispatch each outbox item at least once."""

    def __init__(
        self,
        *,
        store: SQLiteReconciliationStore,
        inbox: ConversationInbox,
        proposals: RemediationProposalSink,
        policy: ReconciliationPolicy | None = None,
    ) -> None:
        self.store = store
        self.inbox = inbox
        self.proposals = proposals
        self.policy = policy or ReconciliationPolicy()

    def enqueue(self, run: ScheduledRunEnvelope) -> DurableEnqueueReceipt:
        decision = self.policy.evaluate(run)
        duplicate, item_ids, persisted_decision = self.store.enqueue(run, decision)
        return DurableEnqueueReceipt(
            decision=persisted_decision,
            duplicate=duplicate,
            outbox_item_ids=item_ids,
        )

    def dispatch_once(
        self,
        owner: str,
        *,
        lease_seconds: float = 60.0,
        now: float | None = None,
    ) -> DispatchReceipt | None:
        item = self.store.claim(
            owner,
            lease_seconds=lease_seconds,
            now=now,
        )
        if item is None:
            return None
        try:
            if item.kind is OutboxKind.EVENT:
                sink_receipt = self.inbox.publish(decode_event(item.payload))
            else:
                sink_receipt = self.proposals.submit(decode_proposal(item.payload))
            if not isinstance(sink_receipt, str) or not sink_receipt.strip():
                raise ValueError("sink receipt must be a non-empty string")
        except Exception as exc:
            self.store.fail(item.item_id, owner, str(exc))
            raise

        # A successful sink call followed by a stale-lease ack is the documented
        # at-least-once crash window. Do not call fail() with the stale owner: it
        # would mask LeaseOwnershipError and could overwrite a new worker's state.
        self.store.ack(item.item_id, owner, sink_receipt, now=now)
        return DispatchReceipt(
            item_id=item.item_id,
            kind=item.kind,
            sink_receipt=sink_receipt,
        )
