from ..types import ResearchAgentState


def synthesize_node(state: ResearchAgentState):
    return {
        "response": f"Synthesizing final answer based on {len(state['visited'])} visited targets and {len(state['current_chunks'])} chunks.",
    }
