# jep-langgraph-adapter

Execution observation, delegation records, and replay archives for LangGraph-style nodes.

This package instruments node callables without modifying LangGraph core. It writes local hash-linked execution records using these instrumentation mappings:

- **Judgment** for node invocation.
- **Delegation** for nodes configured as delegations or explicitly recorded delegation.
- **Termination** for completion, failure, or cancellation.
- **Verification** when a configured application verifier is invoked. Successful execution without a verifier is marked `unchecked` and does not generate a V event.

Each event records `node_name`, `agent_id`, `tool_name`, `state_transition`, `authority_scope`, and `previous_event_hash`.

## Event format and verification scope

This package emits **local runtime envelopes**, not signed [JEP-Core v0.6](https://github.com/hjs-spec/jep-v06) wire events. Its node metadata, event labels, and hash serialization belong to the adapter. It does not produce detached-JWS signatures or perform Core signature and key-trust validation; Core interoperability requires a separately specified mapping and signing implementation.

Keep two checks distinct:

- **Archive replay** checks the supplied records' hashes, sequence, and links.
- **Application verification** records the result of a configured boolean verifier. Its meaning depends on what that callback checks.

A structurally valid archive can contain a failed application check. A V event does not by itself prove a model answer, factual claim, or authorization is correct. The declared `authority_scope` is metadata, not a permission enforcement mechanism.

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

The replay command loads the JSONL records, validates their supplied event hashes, and checks sequence numbers and `previous_event_hash` links. Its `valid` result concerns archive consistency, not application verifier success or complete capture of execution.

The writer appends records, but an unkeyed hash chain alone cannot rule out a complete rewrite or removal of a valid suffix. Detecting those changes requires an independently trusted checkpoint or other external evidence of the expected history.

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
