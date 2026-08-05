"""Thin Hermes adapter contracts; no Hermes private-module imports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable

from .durable import DurableEnqueueReceipt
from .hermes import HermesCronResult, HermesCronResultMapper
from .models import ConversationContextEvent, RemediationProposal
from .serde import event_payload, proposal_payload
from .service import DurableReconciliationService


@runtime_checkable
class HermesConversationIngress(Protocol):
    """Stable Hermes-facing inbox seam implemented by a gateway plugin/hook."""

    def enqueue_context(
        self,
        *,
        platform: str,
        conversation_id: str,
        thread_id: str | None,
        event_id: str,
        payload: Mapping[str, object],
    ) -> str:
        """Durably enqueue structured data for a future conversation turn."""
        ...


@runtime_checkable
class HermesRemediationQueue(Protocol):
    """Governed proposal queue seam; enqueue does not execute remediation."""

    def enqueue_proposal(
        self,
        *,
        proposal_id: str,
        payload: Mapping[str, object],
    ) -> str:
        """Durably enqueue a proposal and return a stable receipt."""
        ...


@dataclass(frozen=True, slots=True)
class HermesConversationInboxAdapter:
    ingress: HermesConversationIngress

    def publish(self, event: ConversationContextEvent) -> str:
        if event.target is None:
            raise ValueError("Hermes conversation event requires a target")
        return self.ingress.enqueue_context(
            platform=event.target.platform,
            conversation_id=event.target.conversation_id,
            thread_id=event.target.thread_id,
            event_id=event.event_id,
            payload=event_payload(event),
        )


@dataclass(frozen=True, slots=True)
class HermesRemediationProposalAdapter:
    queue: HermesRemediationQueue

    def submit(self, proposal: RemediationProposal) -> str:
        return self.queue.enqueue_proposal(
            proposal_id=proposal.proposal_id,
            payload=proposal_payload(proposal),
        )


@dataclass(frozen=True, slots=True)
class HermesCronReconciliationAdapter:
    """Capture a structured Hermes cron result into the durable outbox."""

    service: DurableReconciliationService
    mapper: HermesCronResultMapper = HermesCronResultMapper()

    def capture(self, result: HermesCronResult) -> DurableEnqueueReceipt:
        return self.service.enqueue(self.mapper.map(result))
