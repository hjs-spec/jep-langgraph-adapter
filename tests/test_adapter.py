from pathlib import Path

from jep_langgraph_adapter import JEPEventType, JEPReplayExporter, LangGraphEventAdapter, canonicalize


def test_wrap_node_emits_hash_chain(tmp_path: Path):
    adapter = LangGraphEventAdapter(session_id="test", agent_id="agent", authority_scope={"scope": "local"})

    def node(state):
        return {**state, "done": True}

    wrapped = adapter.wrap_node(node, node_name="node_a")
    assert wrapped({"done": False}) == {"done": True}

    assert [event.event_type for event in adapter.events] == [JEPEventType.JUDGMENT, JEPEventType.TERMINATION]
    assert adapter.events[0].previous_event_hash is None
    assert adapter.events[1].previous_event_hash == adapter.events[0].hash()
    assert adapter.events[0].node_name == "node_a"
    assert adapter.events[0].agent_id == "agent"
    assert adapter.events[0].authority_scope == {"scope": "local"}

    path = adapter.exporter().export_jsonl(tmp_path / "session.jsonl")
    result = JEPReplayExporter.replay_file(path)
    assert result.valid, result.errors


def test_delegation_and_tool_verification_events():
    adapter = LangGraphEventAdapter(session_id="test", verifier=lambda state: state["value"] == 42)

    def tool(state):
        return {"value": state["value"] * 2}

    wrapped = adapter.wrap_node(
        tool,
        node_name="tool_node",
        tool_name="double",
        is_delegation=True,
        delegated_to="tool-agent",
    )
    wrapped({"value": 21})

    assert [event.event_type for event in adapter.events] == [
        JEPEventType.DELEGATION,
        JEPEventType.JUDGMENT,
        JEPEventType.TERMINATION,
        JEPEventType.VERIFICATION,
    ]
    assert adapter.events[0].state_transition["delegated_to"] == "tool-agent"
    assert adapter.events[1].delegation_parent_hash is None
    assert adapter.events[3].tool_name == "double"
    assert adapter.events[3].state_transition["verified"] is True
    assert JEPReplayExporter.replay(adapter.events).valid


def test_canonicalization_is_deterministic():
    left = {"b": [2, 1], "a": {"z": True}}
    right = {"a": {"z": True}, "b": [2, 1]}
    assert canonicalize(left) == canonicalize(right)
