from ..types import ResearchAgentState


def explore_evaluate_node(state: ResearchAgentState):
    return {
        "response": f"Evaluating {len(state['current_chunks'])} chunks from target '{state['current_target']}'",
    }
