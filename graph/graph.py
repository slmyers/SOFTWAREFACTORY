from langgraph.graph import StateGraph, START, END
from graph.state import AgentState
from tools.bootstrap_harness import ensure_harness_scaffolding


ensure_harness_scaffolding()

def chatbot(state: AgentState):
    return {"messages": ["Hello from Software Factory!"]}

graph_builder = StateGraph(AgentState)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()

# Attach LangGraph-compatible saver adapter (no-op marker when DB/migrations
# are not yet present). This keeps graph import safe while wiring the hook.
try:
    from graph.langgraph_saver import attach_langgraph_saver
    attach_langgraph_saver(graph)
except Exception:
    pass
