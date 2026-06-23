from langgraph.graph import StateGraph, START, END

from .nodes.extract_instructions_node import extract_instructions_node
from .nodes.check_existing_repo_node import check_existing_repo_node
from .nodes.clone_repo_node import clone_repo_node
from .nodes.build_repo_map import build_repo_map
from .nodes.generate_keywords_node import generate_keywords_node
from .nodes.explore_search_node import explore_search_node
from .nodes.explore_evaluate_node import explore_evaluate_node
from .nodes.synthesize_output_node import synthesize_output_node

from .nodes.route_nodes import (
    route_after_check_existing_repo_node,
    route_after_clone_repo_node,
    route_after_extract_instructions_node,
    route_after_search,
    route_after_evaluate,
)

from .types import ResearchAgentState
from .memory import checkpointer

graph = StateGraph(ResearchAgentState)

# Define nodes
graph.add_node("extract_instructions_node", extract_instructions_node)
graph.add_node("check_existing_repo_node", check_existing_repo_node)
graph.add_node("clone_repo_node", clone_repo_node)
graph.add_node("build_repo_map", build_repo_map)
graph.add_node("generate_keywords_node", generate_keywords_node)
graph.add_node("explore_search_node", explore_search_node)
graph.add_node("explore_evaluate_node", explore_evaluate_node)
graph.add_node("synthesize_output_node", synthesize_output_node)

# Define edges
graph.add_edge(START, "extract_instructions_node")
graph.add_conditional_edges(
    "extract_instructions_node", route_after_extract_instructions_node
)
graph.add_conditional_edges(
    "check_existing_repo_node", route_after_check_existing_repo_node
)
graph.add_conditional_edges("clone_repo_node", route_after_clone_repo_node)
graph.add_edge("build_repo_map", "generate_keywords_node")
graph.add_edge("generate_keywords_node", "explore_search_node")
graph.add_conditional_edges("explore_search_node", route_after_search)
graph.add_conditional_edges("explore_evaluate_node", route_after_evaluate)
graph.add_edge("synthesize_output_node", END)


# Compile the graph into an agent
agent = graph.compile(checkpointer=checkpointer)
