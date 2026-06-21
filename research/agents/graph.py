from langgraph.graph import StateGraph, START, END

from .nodes.clone_repo_node import clone_repo_node

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


# Define edges
graph.add_edge(START, "extract_instructions_node")
graph.add_conditional_edges(
    "extract_instructions_node", route_after_extract_instructions_node
)
graph.add_edge("clone_repo_node", END)

# Compile the graph into an agent
agent = graph.compile(checkpointer=checkpointer)
