from langgraph.graph import StateGraph, START, END

from .nodes.build_repo_map import build_repo_map
from .nodes.clone_repo_node import clone_repo_node, route_after_clone_repo_node

from .nodes.extract_instructions_node import (
    extract_instructions_node,
    route_after_extract_instructions_node,
)

from .types import ResearchAgentState
from .memory import checkpointer

graph = StateGraph(ResearchAgentState)

# Define nodes
graph.add_node("extract_instructions_node", extract_instructions_node)
graph.add_node("clone_repo_node", clone_repo_node)
graph.add_node("build_repo_map", build_repo_map)

# Define edges
graph.add_edge(START, "extract_instructions_node")
graph.add_conditional_edges(
    "extract_instructions_node", route_after_extract_instructions_node
)
graph.add_conditional_edges("clone_repo_node", route_after_clone_repo_node)
graph.add_edge("build_repo_map", END)

# Compile the graph into an agent
agent = graph.compile(checkpointer=checkpointer)
