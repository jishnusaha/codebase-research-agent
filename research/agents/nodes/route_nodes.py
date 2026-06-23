from typing import Literal

from ..types import ResearchAgentState


def route_after_extract_instructions_node(
    state: ResearchAgentState,
) -> Literal["check_existing_repo_node", "__end__"]:
    if state["should_end"]:
        return "__end__"

    return "check_existing_repo_node"


def route_after_check_existing_repo_node(
    state: ResearchAgentState,
) -> Literal["clone_repo_node", "build_repo_map", "generate_keywords_node"]:
    if state["should_clone"]:
        return "clone_repo_node"
    if state["should_build_repo_map"]:
        return "build_repo_map"
    # If we don't need to clone or build a repo map, we can go straight to generating keywords and exploring the repo.
    return "generate_keywords_node"


def route_after_clone_repo_node(
    state: ResearchAgentState,
) -> Literal["build_repo_map", "__end__"]:
    if state["should_end"]:
        return "__end__"

    return "build_repo_map"


def route_after_search(
    state: ResearchAgentState,
) -> Literal["explore_evaluate_node", "synthesize_output_node"]:
    if state["explore_done"] or not state["current_chunks"]:
        return "synthesize_output_node"
    return "explore_evaluate_node"


def route_after_evaluate(
    state: ResearchAgentState,
) -> Literal["explore_search_node", "synthesize_output_node"]:
    if state["explore_done"]:
        return "synthesize_output_node"
    return "explore_search_node"
