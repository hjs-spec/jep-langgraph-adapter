"""Sub-agent delegation with a delegation parent hash chain."""

from jep_langgraph_adapter import LangGraphEventAdapter


def researcher(state):
    return {**state, "research": "facts gathered by sub-agent"}


adapter = LangGraphEventAdapter(
    session_id="delegation-demo",
    agent_id="supervisor-agent",
    authority_scope={"budget": "low", "allowed_delegatees": ["research-agent"]},
)

research_node = adapter.wrap_node(
    researcher,
    node_name="researcher",
    is_delegation=True,
    delegated_to="research-agent",
    agent_id="supervisor-agent",
)

final_state = research_node({"task": "collect facts"})
adapter.exporter().export_jsonl("examples/out/delegation_session.jsonl")
print(final_state)
