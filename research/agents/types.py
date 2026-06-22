from typing import List, TypedDict, Optional


class RepoFileInfo(TypedDict):
    path: str  # relative path from repo root
    size: int  # bytes
    language: Optional[str]  # inferred from extension
    docstring: Optional[str]  # first docstring/comment, if cheaply extractable


class Finding(TypedDict):
    file: str
    lines: str  # e.g. "42-87"
    note: str  # LLM's short explanation of relevance


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

    # --- populated by generate_keywords_node (Step 1) ---
    search_queue: List[str]
    visited: List[str]  # List not Set — checkpointer must serialize to JSON
    findings: List[Finding]
    iterations: int

    # results and control flow
    should_end: bool
    end_reason: str
    response: str
