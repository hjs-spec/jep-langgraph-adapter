"""Public LangGraph adapter facade."""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional

from .exporter import JEPReplayExporter
from .middleware import JEPNodeMiddleware
from .tracer import JEPExecutionTracer


class LangGraphEventAdapter:
    """Facade for instrumenting LangGraph nodes without patching LangGraph core."""

    def __init__(
        self,
        *,
        session_id: Optional[str] = None,
        agent_id: str = "langgraph-agent",
        authority_scope: Optional[Mapping[str, Any]] = None,
        verifier: Optional[Callable[[Any], bool]] = None,
    ) -> None:
        self.tracer = JEPExecutionTracer(
            session_id=session_id or str(uuid.uuid4()),
            default_agent_id=agent_id,
            default_authority_scope=dict(authority_scope or {}),
        )
        self.middleware = JEPNodeMiddleware(
            self.tracer,
            agent_id=agent_id,
            authority_scope=authority_scope,
            verifier=verifier,
        )

    @property
    def events(self):
        return self.tracer.events

    def wrap_node(self, node: Callable[..., Any], **kwargs: Any) -> Callable[..., Any]:
        return self.middleware.wrap_node(node, **kwargs)

    def wrap_nodes(self, nodes: Mapping[str, Callable[..., Any]], **defaults: Any) -> Dict[str, Callable[..., Any]]:
        return {
            name: self.wrap_node(node, node_name=name, **defaults)
            for name, node in nodes.items()
        }

    def instrument_state_graph(self, graph: Any, nodes: Mapping[str, Callable[..., Any]], **defaults: Any) -> Any:
        """Add wrapped nodes to a LangGraph StateGraph-like object and return the graph."""

        for name, node in nodes.items():
            graph.add_node(name, self.wrap_node(node, node_name=name, **defaults))
        return graph

    def instrument_node_mapping(self, mapping: MutableMapping[str, Callable[..., Any]], **defaults: Any) -> MutableMapping[str, Callable[..., Any]]:
        """Replace callables in a mutable node mapping with wrapped equivalents."""

        for name, node in list(mapping.items()):
            mapping[name] = self.wrap_node(node, node_name=name, **defaults)
        return mapping

    def exporter(self) -> JEPReplayExporter:
        return JEPReplayExporter(self.events)
