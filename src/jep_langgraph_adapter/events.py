"""JEP event model used by the LangGraph adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional

from .canonicalization import canonical_hash, canonicalize


class JEPEventType(str, Enum):
    """JEP accountability event types emitted around LangGraph execution."""

    JUDGMENT = "Judgment Event"
    DELEGATION = "Delegation Event"
    TERMINATION = "Termination Event"
    VERIFICATION = "Verification Event"


@dataclass(frozen=True)
class JEPEvent:
    """A replayable, hash-linked JEP event."""

    event_type: JEPEventType
    event_id: str
    session_id: str
    sequence: int
    node_name: str
    agent_id: str
    tool_name: Optional[str]
    state_transition: Mapping[str, Any]
    authority_scope: Mapping[str, Any]
    previous_event_hash: Optional[str]
    delegation_parent_hash: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    event_hash: Optional[str] = None

    def payload(self, include_hash: bool = False) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "event_type": self.event_type.value,
            "event_id": self.event_id,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "node_name": self.node_name,
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "state_transition": dict(self.state_transition),
            "authority_scope": dict(self.authority_scope),
            "previous_event_hash": self.previous_event_hash,
            "delegation_parent_hash": self.delegation_parent_hash,
            "metadata": dict(self.metadata),
        }
        if include_hash:
            data["event_hash"] = self.hash()
        return data

    def hash(self) -> str:
        return self.event_hash or canonical_hash(self.payload(include_hash=False))

    def to_json(self) -> str:
        return canonicalize(self.payload(include_hash=True))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "JEPEvent":
        event_hash = data.get("event_hash")
        event = cls(
            event_type=JEPEventType(data["event_type"]),
            event_id=str(data["event_id"]),
            session_id=str(data["session_id"]),
            sequence=int(data["sequence"]),
            node_name=str(data["node_name"]),
            agent_id=str(data["agent_id"]),
            tool_name=data.get("tool_name"),
            state_transition=data.get("state_transition", {}),
            authority_scope=data.get("authority_scope", {}),
            previous_event_hash=data.get("previous_event_hash"),
            delegation_parent_hash=data.get("delegation_parent_hash"),
            metadata=data.get("metadata", {}),
            event_hash=event_hash,
        )
        expected = event.hash() if event_hash is None else canonical_hash(event.payload(include_hash=False))
        if event_hash is not None and event_hash != expected:
            raise ValueError(f"event_hash mismatch for {event.event_id}: expected {expected}, got {event_hash}")
        return event
