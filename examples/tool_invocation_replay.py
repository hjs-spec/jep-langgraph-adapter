"""Tool invocation example that emits verification events and can be replayed."""

from jep_langgraph_adapter import JEPReplayExporter, LangGraphEventAdapter


def calculator_tool(state):
    return {**state, "tool_result": state["x"] + state["y"]}


adapter = LangGraphEventAdapter(
    session_id="tool-replay-demo",
    agent_id="math-agent",
    authority_scope={"tools": ["calculator"], "max_tool_calls": 1},
    verifier=lambda state: state.get("tool_result") == 5,
)

node = adapter.wrap_node(calculator_tool, node_name="calculator_node", tool_name="calculator")
node({"x": 2, "y": 3})
path = adapter.exporter().export_jsonl("examples/out/tool_session.jsonl")
result = JEPReplayExporter.replay_file(path)
print(f"replay_valid={result.valid} events={len(result.events)}")
