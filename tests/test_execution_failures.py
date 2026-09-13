import asyncio
from concurrent.futures import ThreadPoolExecutor
import pytest
from jep_langgraph_adapter import LangGraphEventAdapter, JEPEventType


def test_tool_without_verifier_is_unchecked():
    adapter = LangGraphEventAdapter()
    adapter.wrap_node(lambda s: s, tool_name="echo")({})
    assert [e.event_type for e in adapter.events] == [JEPEventType.JUDGMENT, JEPEventType.TERMINATION]
    assert adapter.events[-1].metadata["verification_status"] == "unchecked"


def test_failure_closes_event_and_preserves_input_snapshot():
    adapter = LangGraphEventAdapter()
    def fail(state):
        state["value"] = 2
        raise RuntimeError("failed")
    with pytest.raises(RuntimeError):
        adapter.wrap_node(fail)({"value": 1})
    assert adapter.events[-1].metadata["status"] == "failed"
    assert adapter.events[0].state_transition["input_state_hash"] == adapter.events[-1].state_transition["input_state_hash"]


def test_async_cancellation_and_async_verifier():
    async def run():
        cancelled = LangGraphEventAdapter()
        async def cancel(state):
            raise asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await cancelled.wrap_node(cancel)({})
        assert cancelled.events[-1].metadata["status"] == "cancelled"
        async def verify(state):
            await asyncio.sleep(0)
            return False
        adapter = LangGraphEventAdapter(verifier=verify)
        async def node(state):
            return state
        await adapter.wrap_node(node)({})
        assert adapter.events[-1].state_transition["verified"] is False
    asyncio.run(run())


def test_verifier_must_return_boolean_and_errors_are_recorded():
    adapter = LangGraphEventAdapter(verifier=lambda s: "yes")
    with pytest.raises(TypeError):
        adapter.wrap_node(lambda s: s)({})
    assert adapter.events[-1].state_transition["verified"] is False
    assert adapter.events[-1].metadata["status"] == "error"


def test_parallel_nodes_keep_unique_sequence_and_hash_chain():
    adapter = LangGraphEventAdapter()
    node = adapter.wrap_node(lambda s: s)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(node, range(40)))
    assert [e.sequence for e in adapter.events] == list(range(80))
    assert all(e.previous_event_hash == p.hash() for p, e in zip(adapter.events, adapter.events[1:]))
