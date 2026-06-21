from typing import TypedDict


class ResearchAgentState(TypedDict):
    """Represents the state of an agent in the research process."""

    original_question: str

    repo_url: str
    question: str

    should_end: bool
    end_reason: str
    response: str
