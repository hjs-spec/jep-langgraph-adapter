# jep-langgraph-adapter

JEP runtime adapter for LangGraph: replayable delegation and verifiable AI accountability semantics.

This package instruments LangGraph-style node callables without modifying LangGraph core. Wrapped node execution naturally emits a deterministic, hash-linked JEP accountability chain containing:

- Judgment Event
- Delegation Event
- Termination Event
- Verification Event

Each event records `node_name`, `agent_id`, `tool_name`, `state_transition`, `authority_scope`, and `previous_event_hash`.

## Install

```bash
pip install -e .
```

LangGraph is optional for tests and examples because the adapter works at the callable-node boundary:

```bash
pip install -e '.[langgraph]'
```

## Usage

```python
from jep_langgraph_adapter import LangGraphEventAdapter

adapter = LangGraphEventAdapter(
    session_id="demo-session",
    agent_id="planner-agent",
    authority_scope={"tools": ["search"], "max_steps": 3},
)

def plan(state):
    return {**state, "plan": "call search"}

wrapped_plan = adapter.wrap_node(plan, node_name="plan")
next_state = wrapped_plan({"question": "What changed?"})
adapter.exporter().export_jsonl("session.jsonl")
```

For a `StateGraph`, add wrapped nodes through `instrument_state_graph`:

```python
adapter.instrument_state_graph(graph, {"plan": plan, "answer": answer})
```

## Replay CLI

```bash
jep-langgraph replay session.jsonl
```

The replay command validates deterministic event hashes, sequence numbers, and `previous_event_hash` links.

## Components

- `JEPNodeMiddleware`: wraps sync or async LangGraph node callables.
- `JEPExecutionTracer`: records judgment, delegation, termination, and verification events.
- `JEPReplayExporter`: exports JSON/JSONL and validates replay chains.
- `LangGraphEventAdapter`: high-level facade for node and graph instrumentation.

## Examples

- `examples/multi_step_graph.py`: multi-step graph execution.
- `examples/sub_agent_delegation.py`: sub-agent delegation chain.
- `examples/tool_invocation_replay.py`: tool invocation verification and replay.

## Runtime and verification notes

See [HARDENING.md](HARDENING.md) for supported behavior, regression checks, and compatibility boundaries.
