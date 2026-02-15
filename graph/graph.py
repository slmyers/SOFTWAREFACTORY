from langgraph.graph import StateGraph, START, END
from graph.state import AgentState

def chatbot(state: AgentState):
    return {"messages": ["Hello from Software Factory!"]}

graph_builder = StateGraph(AgentState)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()