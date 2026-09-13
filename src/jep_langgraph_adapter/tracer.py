"""Execution tracer that emits JEP accountability events."""

from __future__ import annotations

import contextvars
import uuid
from copy import deepcopy
from threading import RLock
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from .canonicalization import canonical_hash
from .events import JEPEvent, JEPEventType


@dataclass
class JEPExecutionTracer:
    """Collects a deterministic chain of JEP events for a LangGraph run."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    default_agent_id: str = "langgraph-agent"
    default_authority_scope: Mapping[str, Any] = field(default_factory=dict)
    events: List[JEPEvent] = field(default_factory=list)
    _lock: Any = field(default_factory=RLock, repr=False)
    _delegation_hash: Any = field(
        default_factory=lambda: contextvars.ContextVar(
            "jep_delegation_hash", default=None
        ),
        repr=False,
    )

    @property
    def previous_event_hash(self) -> Optional[str]:
        return self.events[-1].hash() if self.events else None

    def record_judgment(
        self,
        *,
        node_name: str,
        agent_id: Optional[str],
        input_state: Any,
        authority_scope: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> JEPEvent:
        return self._append(
            JEPEventType.JUDGMENT,
            node_name=node_name,
            agent_id=agent_id,
            tool_name=None,
            state_transition={
                "phase": "before_node",
                "input_state_hash": canonical_hash(input_state),
                "output_state_hash": None,
            },
            authority_scope=authority_scope,
            metadata=metadata,
        )

    def record_delegation(
        self,
        *,
        node_name: str,
        agent_id: Optional[str],
        delegated_to: str,
        tool_name: Optional[str] = None,
        state: Any = None,
        authority_scope: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> JEPEvent:
        parent_hash = self._delegation_hash.get() or self.previous_event_hash
        return self._append(
            JEPEventType.DELEGATION,
            node_name=node_name,
            agent_id=agent_id,
            tool_name=tool_name,
            state_transition={
                "phase": "delegation",
                "state_hash": canonical_hash(state),
                "delegated_to": delegated_to,
            },
            authority_scope=authority_scope,
            delegation_parent_hash=parent_hash,
            metadata=metadata,
        )

    def record_termination(
        self,
        *,
        node_name: str,
        agent_id: Optional[str],
        input_state: Any,
        output_state: Any,
        authority_scope: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> JEPEvent:
        return self._append(
            JEPEventType.TERMINATION,
            node_name=node_name,
            agent_id=agent_id,
            tool_name=None,
            state_transition={
                "phase": "after_node",
                "input_state_hash": canonical_hash(input_state),
                "output_state_hash": canonical_hash(output_state),
            },
            authority_scope=authority_scope,
            metadata=metadata,
        )

    def record_verification(
        self,
        *,
        node_name: str,
        agent_id: Optional[str],
        tool_name: Optional[str],
        state: Any,
        verified: bool,
        authority_scope: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> JEPEvent:
        return self._append(
            JEPEventType.VERIFICATION,
            node_name=node_name,
            agent_id=agent_id,
            tool_name=tool_name,
            state_transition={
                "phase": "verification",
                "state_hash": canonical_hash(state),
                "verified": verified,
            },
            authority_scope=authority_scope,
            metadata=metadata,
        )

    def delegation_context(self, delegation_event: JEPEvent):
        """Return a context manager that records nested events under a delegation hash."""

        class _DelegationContext:
            def __enter__(self_inner):
                self_inner.token = self._delegation_hash.set(delegation_event.hash())
                return delegation_event

            def __exit__(self_inner, exc_type, exc, tb):
                self._delegation_hash.reset(self_inner.token)
                return False

        return _DelegationContext()

    def _append(
        self,
        event_type: JEPEventType,
        *,
        node_name: str,
        agent_id: Optional[str],
        tool_name: Optional[str],
        state_transition: Mapping[str, Any],
        authority_scope: Optional[Mapping[str, Any]],
        delegation_parent_hash: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> JEPEvent:
        with self._lock:
            event = JEPEvent(
                event_type=event_type,
                event_id=f"{self.session_id}:{len(self.events)}",
                session_id=self.session_id,
                sequence=len(self.events),
                node_name=node_name,
                agent_id=agent_id or self.default_agent_id,
                tool_name=tool_name,
                state_transition=deepcopy(dict(state_transition)),
                authority_scope=deepcopy(
                    dict(
                        authority_scope
                        if authority_scope is not None
                        else self.default_authority_scope
                    )
                ),
                previous_event_hash=self.previous_event_hash,
                delegation_parent_hash=delegation_parent_hash,
                metadata=deepcopy(dict(metadata or {})),
            )
            event = JEPEvent.from_mapping(event.payload(include_hash=True))
            self.events.append(event)
            return event
