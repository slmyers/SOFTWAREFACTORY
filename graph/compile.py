"""Graph factory for SOFTWAREFACTORY (Issue #9).

`compile_graph()` is the single function everyone should call to get a
runnable LangGraph app.  It wires all 9 agent-node stubs together with the
Supervisor as the central conditional router.

Node pipeline (stub order):
    spec_parser → architect → planner → coder → executor
    → sandbox → reviewer → refiner → doc_gardener

Every agent node sets ``state["next"]`` to its own name before returning so
the Supervisor knows which step just completed and can advance the pipeline
or redirect on quality / invariant failures.

Topology
--------
START → spec_parser
Each agent node → supervisor (fixed)
supervisor → (conditional) → any agent node  |  END

The conditional routing key is ``state["next"]`` which the supervisor node
populates each time it runs.
"""

from __future__ import annotations

from typing import Any, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from agents.spec_parser import spec_parser_node  # Issue #11
from agents.supervisor import Supervisor
from graph.state import AgentState

__all__ = ["compile_graph"]

# ---------------------------------------------------------------------------
# Pipeline order — used by the supervisor to advance on "next_node" decisions
# ---------------------------------------------------------------------------
PIPELINE: list[str] = [
    "spec_parser",
    "architect",
    "planner",
    "coder",
    "executor",
    "sandbox",
    "reviewer",
    "refiner",
    "doc_gardener",
]

# Map supervisor semantic route names → real graph node names (or END)
# These names come from Supervisor.decide_next_node() return values.
_SEMANTIC_TO_NODE: dict[str, Any] = {
    "improvement_agent": "coder",  # low-quality → recode
    "refinement_agent": "refiner",  # medium-quality → refine
    "invariant_agent": "reviewer",  # invariant failure → review
    "test_fix_agent": "coder",  # test failure → recode
    "human_pause": END,  # human interrupt → stop
    "next_node": None,  # advance pipeline — resolved at runtime
}


# ---------------------------------------------------------------------------
# Stub agent nodes
# Each node records its own name in state["next"] so the supervisor knows
# who just ran.  Real implementations (Issues #11-19) will replace these.
# ---------------------------------------------------------------------------


def _make_stub(node_name: str):
    """Return a pass-through stub node that marks itself as the current step."""

    def _node(state: AgentState) -> dict:
        return {"next": node_name}

    _node.__name__ = f"{node_name}_node"
    return _node


architect_node = _make_stub("architect")  # Issue #12
planner_node = _make_stub("planner")  # Issue #13
coder_node = _make_stub("coder")  # Issue #14
executor_node = _make_stub("executor")  # Issue #15
sandbox_node = _make_stub("sandbox")  # Issue #16
reviewer_node = _make_stub("reviewer")  # Issue #17
refiner_node = _make_stub("refiner")  # Issue #18
doc_gardener_node = _make_stub("doc_gardener")  # Issue #19


# ---------------------------------------------------------------------------
# Supervisor node
# Wraps Supervisor.decide_next_node() and writes the resolved node name
# (or END sentinel "__end__") into state["next"].
# ---------------------------------------------------------------------------


def supervisor_node(state: AgentState) -> dict:
    """Consult the Supervisor and record the next routing target in state."""
    current = state.get("next") or "spec_parser"

    decision = Supervisor().decide_next_node(
        current_node=current,
        quality_score=state.get("quality_score", 0.0),
        invariants_ok=len(state.get("invariants") or []) == 0,
        test_results=(state.get("test_results") or None),
        human_pause=False,
    )

    semantic_route = decision.get("next_node", "improvement_agent")

    if semantic_route == "next_node":
        # Advance to the next stage in the linear pipeline
        if current in PIPELINE:
            idx = PIPELINE.index(current)
            next_target: Any = PIPELINE[idx + 1] if idx + 1 < len(PIPELINE) else END
        else:
            next_target = END
    else:
        next_target = _SEMANTIC_TO_NODE.get(semantic_route, "coder")

    # LangGraph uses the string "__end__" internally for the END sentinel
    resolved = "__end__" if next_target is END else next_target
    return {"next": resolved}


# ---------------------------------------------------------------------------
# Conditional edge function — reads state["next"] to choose the next node
# ---------------------------------------------------------------------------


def _route_from_supervisor(state: AgentState) -> str:
    """Conditional edge: return node name or END based on state['next']."""
    target = state.get("next", "coder")
    return target if target != "__end__" else END


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------


def compile_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """Build and compile the LangGraph state machine.

    Parameters
    ----------
    checkpointer:
        Optional LangGraph checkpointer (e.g. MemorySaver, AsyncPostgresSaver).
        When None the graph runs without persistence (useful for tests).

    Returns
    -------
    CompiledStateGraph
        A ready-to-invoke LangGraph app.
    """
    builder = StateGraph(AgentState)

    # --- Register all nodes ------------------------------------------------
    builder.add_node("spec_parser", spec_parser_node)
    builder.add_node("architect", architect_node)
    builder.add_node("planner", planner_node)
    builder.add_node("coder", coder_node)
    builder.add_node("executor", executor_node)
    builder.add_node("sandbox", sandbox_node)
    builder.add_node("reviewer", reviewer_node)
    builder.add_node("refiner", refiner_node)
    builder.add_node("doc_gardener", doc_gardener_node)
    builder.add_node("supervisor", supervisor_node)

    # --- Entry edge --------------------------------------------------------
    # Always start with spec parsing
    builder.add_edge(START, "spec_parser")

    # --- Fixed edges: every agent node reports back to the supervisor ------
    for node_name in PIPELINE:
        builder.add_edge(node_name, "supervisor")

    # --- Conditional edge: supervisor fans out to the appropriate node -----
    builder.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {
            "spec_parser": "spec_parser",
            "architect": "architect",
            "planner": "planner",
            "coder": "coder",
            "executor": "executor",
            "sandbox": "sandbox",
            "reviewer": "reviewer",
            "refiner": "refiner",
            "doc_gardener": "doc_gardener",
            END: END,
        },
    )

    # --- Compile -----------------------------------------------------------
    compile_kwargs: dict = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    return builder.compile(**compile_kwargs)
