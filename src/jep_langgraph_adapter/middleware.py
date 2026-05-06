"""LangGraph node middleware that wraps node callables without modifying LangGraph core."""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable, Mapping, Optional

from .tracer import JEPExecutionTracer


class JEPNodeMiddleware:
    """Wrap LangGraph node execution and emit JEP events automatically."""

    def __init__(
        self,
        tracer: Optional[JEPExecutionTracer] = None,
        *,
        agent_id: Optional[str] = None,
        authority_scope: Optional[Mapping[str, Any]] = None,
        verifier: Optional[Callable[[Any], bool]] = None,
    ) -> None:
        self.tracer = tracer or JEPExecutionTracer()
        self.agent_id = agent_id
        self.authority_scope = dict(authority_scope or {})
        self.verifier = verifier

    def wrap_node(
        self,
        node: Callable[..., Any],
        *,
        node_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        authority_scope: Optional[Mapping[str, Any]] = None,
        is_delegation: bool = False,
        delegated_to: Optional[str] = None,
    ) -> Callable[..., Any]:
        """Return a wrapped node callable that records judgment/termination/verification events."""

        resolved_node_name = node_name or getattr(node, "__name__", node.__class__.__name__)
        resolved_agent_id = agent_id or self.agent_id
        resolved_scope = dict(authority_scope or self.authority_scope)

        if inspect.iscoroutinefunction(node):

            @wraps(node)
            async def async_wrapper(state: Any, *args: Any, **kwargs: Any) -> Any:
                delegation_event = self._maybe_record_delegation(
                    is_delegation=is_delegation,
                    delegated_to=delegated_to,
                    node_name=resolved_node_name,
                    agent_id=resolved_agent_id,
                    tool_name=tool_name,
                    state=state,
                    authority_scope=resolved_scope,
                )
                context = self.tracer.delegation_context(delegation_event) if delegation_event else _NullContext()
                with context:
                    self.tracer.record_judgment(
                        node_name=resolved_node_name,
                        agent_id=resolved_agent_id,
                        input_state=state,
                        authority_scope=resolved_scope,
                        metadata={"callable": repr(node)},
                    )
                    result = await node(state, *args, **kwargs)
                    self._record_completion(
                        node_name=resolved_node_name,
                        agent_id=resolved_agent_id,
                        tool_name=tool_name,
                        input_state=state,
                        output_state=result,
                        authority_scope=resolved_scope,
                    )
                    return result

            return async_wrapper

        @wraps(node)
        def wrapper(state: Any, *args: Any, **kwargs: Any) -> Any:
            delegation_event = self._maybe_record_delegation(
                is_delegation=is_delegation,
                delegated_to=delegated_to,
                node_name=resolved_node_name,
                agent_id=resolved_agent_id,
                tool_name=tool_name,
                state=state,
                authority_scope=resolved_scope,
            )
            context = self.tracer.delegation_context(delegation_event) if delegation_event else _NullContext()
            with context:
                self.tracer.record_judgment(
                    node_name=resolved_node_name,
                    agent_id=resolved_agent_id,
                    input_state=state,
                    authority_scope=resolved_scope,
                    metadata={"callable": repr(node)},
                )
                result = node(state, *args, **kwargs)
                self._record_completion(
                    node_name=resolved_node_name,
                    agent_id=resolved_agent_id,
                    tool_name=tool_name,
                    input_state=state,
                    output_state=result,
                    authority_scope=resolved_scope,
                )
                return result

        return wrapper

    def record_delegation(self, **kwargs: Any):
        """Record an explicit sub-agent delegation event from user graph code."""

        return self.tracer.record_delegation(**kwargs)

    def _maybe_record_delegation(
        self,
        *,
        is_delegation: bool,
        delegated_to: Optional[str],
        node_name: str,
        agent_id: Optional[str],
        tool_name: Optional[str],
        state: Any,
        authority_scope: Mapping[str, Any],
    ):
        if not is_delegation:
            return None
        return self.tracer.record_delegation(
            node_name=node_name,
            agent_id=agent_id,
            delegated_to=delegated_to or node_name,
            tool_name=tool_name,
            state=state,
            authority_scope=authority_scope,
        )

    def _record_completion(
        self,
        *,
        node_name: str,
        agent_id: Optional[str],
        tool_name: Optional[str],
        input_state: Any,
        output_state: Any,
        authority_scope: Mapping[str, Any],
    ) -> None:
        self.tracer.record_termination(
            node_name=node_name,
            agent_id=agent_id,
            input_state=input_state,
            output_state=output_state,
            authority_scope=authority_scope,
        )
        if tool_name or self.verifier:
            verified = bool(self.verifier(output_state)) if self.verifier else True
            self.tracer.record_verification(
                node_name=node_name,
                agent_id=agent_id,
                tool_name=tool_name,
                state=output_state,
                verified=verified,
                authority_scope=authority_scope,
            )


class _NullContext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False
