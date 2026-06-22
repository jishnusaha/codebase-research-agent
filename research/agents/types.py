from typing import List, TypedDict, Optional


class ResearchAgentState(TypedDict):
    """Represents the state of an agent in the research process."""

    original_question: str

    # --- populated by extract_instructions_node ---
    repo_url: str
    question: str

    # --- populated by clone_repo_node ---
    repo_path: str  # local filesystem path to cloned repo

    # results and control flow
    should_end: bool
    end_reason: str
    response: str
