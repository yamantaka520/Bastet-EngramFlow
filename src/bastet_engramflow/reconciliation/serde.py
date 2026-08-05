"""Canonical JSON codecs for durable reconciliation payloads."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from bastet_engramflow.runtimes import ArtifactReference

from .models import (
    ActionClass,
    ConversationContextEvent,
    ConversationReference,
    FindingSeverity,
    ReconciliationDecision,
    RemediationDisposition,
    RemediationProposal,
    RunOutcome,
    ScheduledFinding,
    ScheduledRunEnvelope,
)


def _value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        converted = [_value(item) for item in value]
        return sorted(converted, key=lambda item: canonical_json(item))
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return getattr(value, "value")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported durable payload value: {type(value).__name__}")


def canonical_json(value: object) -> str:
    """Encode a JSON-compatible value deterministically."""
    return json.dumps(
        _value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _reference(value: ConversationReference | None) -> dict[str, object] | None:
    if value is None:
        return None
    return {
        "platform": value.platform,
        "conversation_id": value.conversation_id,
        "thread_id": value.thread_id,
    }


def _finding(value: ScheduledFinding) -> dict[str, object]:
    return {
        "finding_id": value.finding_id,
        "severity": value.severity.value,
        "code": value.code,
        "message": value.message,
        "retryable": value.retryable,
        "action_class": value.action_class.value,
        "suggested_action": value.suggested_action,
        "acceptance_criteria": list(value.acceptance_criteria),
        "metadata": _value(value.metadata),
    }


def _artifact(value: ArtifactReference) -> dict[str, object]:
    return {
        "kind": value.kind,
        "uri": value.uri,
        "digest": value.digest,
        "metadata": _value(value.metadata),
    }


def run_payload(run: ScheduledRunEnvelope) -> dict[str, object]:
    return {
        "schedule_id": run.schedule_id,
        "run_id": run.run_id,
        "occurred_at": run.occurred_at.isoformat(),
        "outcome": run.outcome.value,
        "summary": run.summary,
        "origin": _reference(run.origin),
        "findings": [_finding(item) for item in run.findings],
        "artifacts": [_artifact(item) for item in run.artifacts],
        "remediation_idempotency_key": run.remediation_idempotency_key,
        "continuation_depth": run.continuation_depth,
        "parent_run_id": run.parent_run_id,
        "metadata": _value(run.metadata),
    }


def event_payload(event: ConversationContextEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "schedule_id": event.schedule_id,
        "run_id": event.run_id,
        "target": _reference(event.target),
        "occurred_at": event.occurred_at.isoformat(),
        "outcome": event.outcome.value,
        "summary": event.summary,
        "findings": [_finding(item) for item in event.findings],
        "artifacts": [_artifact(item) for item in event.artifacts],
    }


def proposal_payload(proposal: RemediationProposal) -> dict[str, object]:
    return {
        "proposal_id": proposal.proposal_id,
        "schedule_id": proposal.schedule_id,
        "source_run_id": proposal.source_run_id,
        "why_now": proposal.why_now,
        "findings": [_finding(item) for item in proposal.findings],
        "idempotency_key": proposal.idempotency_key,
        "continuation_depth": proposal.continuation_depth,
        "requires_approval": proposal.requires_approval,
    }


def decision_payload(decision: ReconciliationDecision) -> dict[str, object]:
    return {
        "event": event_payload(decision.event),
        "disposition": decision.disposition.value,
        "proposal": (
            proposal_payload(decision.proposal)
            if decision.proposal is not None
            else None
        ),
        "reasons": sorted(decision.reasons),
        "problem_resolved": decision.problem_resolved,
    }


def _load_reference(value: object) -> ConversationReference | None:
    if value is None:
        return None
    data = _dict(value)
    return ConversationReference(
        platform=str(data["platform"]),
        conversation_id=str(data["conversation_id"]),
        thread_id=str(data["thread_id"]) if data.get("thread_id") is not None else None,
    )


def _load_finding(value: object) -> ScheduledFinding:
    data = _dict(value)
    return ScheduledFinding(
        finding_id=str(data["finding_id"]),
        severity=FindingSeverity(str(data["severity"])),
        code=str(data["code"]),
        message=str(data["message"]),
        retryable=bool(data["retryable"]),
        action_class=ActionClass(str(data["action_class"])),
        suggested_action=str(data["suggested_action"]),
        acceptance_criteria=tuple(
            str(item) for item in _list(data.get("acceptance_criteria", []))
        ),
        metadata=_dict(data.get("metadata", {})),
    )


def _load_artifact(value: object) -> ArtifactReference:
    data = _dict(value)
    return ArtifactReference(
        kind=str(data["kind"]),
        uri=str(data["uri"]),
        digest=str(data["digest"]) if data.get("digest") is not None else None,
        metadata=_dict(data.get("metadata", {})),
    )


def decode_event(payload: str) -> ConversationContextEvent:
    data = _dict(json.loads(payload))
    return ConversationContextEvent(
        event_id=str(data["event_id"]),
        schedule_id=str(data["schedule_id"]),
        run_id=str(data["run_id"]),
        target=_load_reference(data.get("target")),
        occurred_at=datetime.fromisoformat(str(data["occurred_at"])),
        outcome=RunOutcome(str(data["outcome"])),
        summary=str(data["summary"]),
        findings=tuple(_load_finding(item) for item in _list(data.get("findings", []))),
        artifacts=tuple(
            _load_artifact(item) for item in _list(data.get("artifacts", []))
        ),
    )


def decode_proposal(payload: str) -> RemediationProposal:
    data = _dict(json.loads(payload))
    return RemediationProposal(
        proposal_id=str(data["proposal_id"]),
        schedule_id=str(data["schedule_id"]),
        source_run_id=str(data["source_run_id"]),
        why_now=str(data["why_now"]),
        findings=tuple(_load_finding(item) for item in _list(data.get("findings", []))),
        idempotency_key=str(data["idempotency_key"])
        if data.get("idempotency_key") is not None
        else None,
        continuation_depth=int(data["continuation_depth"]),
        requires_approval=bool(data["requires_approval"]),
    )


def decode_decision(payload: str) -> ReconciliationDecision:
    data = _dict(json.loads(payload))
    proposal = data.get("proposal")
    return ReconciliationDecision(
        event=decode_event(canonical_json(data["event"])),
        disposition=RemediationDisposition(str(data["disposition"])),
        proposal=(
            decode_proposal(canonical_json(proposal)) if proposal is not None else None
        ),
        reasons=frozenset(str(item) for item in _list(data.get("reasons", []))),
        problem_resolved=bool(data.get("problem_resolved", False)),
    )


def _dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("durable payload must contain an object")
    return value


def _list(value: object) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError("durable payload field must contain a list")
    return value
