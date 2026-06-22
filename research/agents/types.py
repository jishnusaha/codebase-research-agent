from typing import List, TypedDict, Optional


class RepoFileInfo(TypedDict):
    path: str  # relative path from repo root
    size: int  # bytes
    language: Optional[str]  # inferred from extension
    docstring: Optional[str]  # first docstring/comment, if cheaply extractable


class ResearchAgentState(TypedDict):
    """Represents the state of an agent in the research process."""

    original_question: str

    # --- populated by extract_instructions_node ---
    repo_url: str
    question: str

    # --- populated by clone_repo_node ---
    repo_path: str  # local filesystem path to cloned repo

    # --- populated by build_repo_map_node ---
    repo_map: List[RepoFileInfo]
    primary_language: Optional[str]

    # results and control flow
    should_end: bool
    end_reason: str
    response: str
