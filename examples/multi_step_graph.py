"""Minimal multi-step LangGraph-style execution with automatic JEP events."""

from jep_langgraph_adapter import LangGraphEventAdapter


def plan(state):
    return {**state, "plan": ["search", "summarize"]}


def summarize(state):
    return {**state, "answer": "summary ready"}


adapter = LangGraphEventAdapter(
    session_id="multi-step-demo",
    agent_id="planner-agent",
    authority_scope={"can_call_tools": False, "max_steps": 2},
)

nodes = adapter.wrap_nodes({"plan": plan, "summarize": summarize})
state = {"question": "What happened?"}
state = nodes["plan"](state)
state = nodes["summarize"](state)

adapter.exporter().export_jsonl("examples/out/multi_step_session.jsonl")
print(f"exported {len(adapter.events)} events")
