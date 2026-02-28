"""Backward-compatibility shim — exports the compiled graph for langgraph.json.

Do not add logic here.  See graph/compile.py for the canonical factory.
"""

from graph.compile import compile_graph
from tools.bootstrap_harness import ensure_harness_scaffolding

ensure_harness_scaffolding()

# LangGraph Studio / langgraph.json resolve this module-level object
graph = compile_graph()
