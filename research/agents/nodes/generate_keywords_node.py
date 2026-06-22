from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from ..types import ResearchAgentState, RepoFileInfo

# How many files to include in the repo map sent to the LLM.
# Beyond ~150 paths the prompt bloats without much signal gain.
REPO_MAP_FILE_LIMIT = 150


class GenerateKeywordsOutput(BaseModel):
    keywords: list[str] = Field(
        description=(
            "Ordered list of search targets to start exploration. "
            "Each entry is either a symbol name (function, class, variable, decorator), "
            "a string literal, or a relative file path. "
            "Most specific / most likely leads first."
        )
    )
    reasoning: str = Field(
        description="One short paragraph explaining why these are good starting points."
    )


def _build_repo_map_prompt_block(
    repo_map: list[RepoFileInfo]
) -> str:
    """
    Condense the repo map down to a prompt-friendly block.
    Drops asset/lockfiles (no language tag), caps at REPO_MAP_FILE_LIMIT entries.
    """
    # Only include files we can actually search/parse
    code_files = [f for f in repo_map if f["language"] is not None]

    # Sort: files with docstrings first (more informative), then by path
    code_files.sort(key=lambda f: (f["docstring"] is None, f["path"]))

    # Cap
    included = code_files[:REPO_MAP_FILE_LIMIT]
    truncated = len(code_files) - len(included)

    lines = []
    for f in included:
        lang_tag = f"[{f['language']}]"
        doc_tag = f" — {f['docstring']}" if f["docstring"] else ""
        lines.append(f"  {f['path']} {lang_tag}{doc_tag}")

    block = "\n".join(lines)
    if truncated > 0:
        block += f"\n  ... ({truncated} more files not shown)"

    return block


def generate_keywords_node(state: ResearchAgentState):
    repo_map_block = _build_repo_map_prompt_block(
        state["repo_map"]
     
    )

    prompt = f"""
        You are the planning step of a codebase research agent.

        RESEARCH QUESTION:
        {state["question"]}

        PRIMARY LANGUAGE: {state.get("primary_language") or "unknown"}

        REPOSITORY FILE TREE (code files only):
        {repo_map_block}

        Your job: propose the initial set of search targets that will let the agent
        answer the research question by exploring the codebase.

        A search target can be:
        - A symbol name: function, class, method, variable, decorator, constant
        (e.g. "solve_dependencies", "AuthMiddleware", "RATE_LIMIT")
        - A string literal used in the code
        (e.g. "dependency_overrides", "X-Request-Id")
        - A relative file path if the answer is obviously in a specific file
        (e.g. "auth/backends.py")

        Rules:
        - Return 5–10 targets. More is fine if the question is broad.
        - Order them: most specific / highest-confidence leads first.
        - Do NOT return generic terms like "import", "class", "def" — they'll
        match everything and are useless.
        - Prefer symbols over file paths unless a file path is uniquely informative.
        - Reason from the file tree and the question — don't just echo words
        from the question back as keywords.
    """

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(
        GenerateKeywordsOutput
    )

    result: GenerateKeywordsOutput = llm.invoke(prompt)

    return {
        "search_queue": result.keywords,
        "visited": [],
        "findings": [],
        "iterations": 0,
    }
