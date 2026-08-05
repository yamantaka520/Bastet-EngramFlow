"""Ports implemented by conversation and proposal delivery adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import ConversationContextEvent, RemediationProposal


@runtime_checkable
class ConversationInbox(Protocol):
    """Idempotent event sink keyed by event_id, including repeated retries."""

    def publish(self, event: ConversationContextEvent) -> str:
        """Persist/deliver an event and return a stable receipt."""
        ...


@runtime_checkable
class RemediationProposalSink(Protocol):
    """Idempotent proposal sink keyed by proposal_id, including repeated retries."""

    def submit(self, proposal: RemediationProposal) -> str:
        """Persist a proposal and return a stable receipt."""
        ...
