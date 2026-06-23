from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from ..types import ResearchAgentState, Finding

from .utils import looks_like_file_path


MAX_ITERATIONS = 20
MAX_CHUNK_CHARS = 3000  # per chunk — keeps prompt size bounded


class EvaluateChunkOutput(BaseModel):
    is_relevant: bool = Field(
        description="True if these chunks meaningfully help answer the research question."
    )
    note: str = Field(
        description=(
            "If relevant: one short paragraph explaining exactly what this chunk reveals "
            "about the question. If not relevant: one sentence explaining why it was a dead end."
        )
    )
    next_search_targets: list[str] = Field(
        default_factory=list,
        description=(
            "New symbol names, string literals, or file paths to search next. "
            "Only include targets that would genuinely deepen the answer — "
            "not things already covered by the findings so far."
        ),
    )
    done: bool = Field(
        description=(
            "True if the findings accumulated so far are sufficient to give a complete, "
            "well-cited answer to the research question. Be conservative — only set True "
            "when the core mechanism is understood, not just partially glimpsed."
        )
    )


def explore_evaluate_node(state: ResearchAgentState) -> dict:
    chunks = state["current_chunks"]
    findings = state["findings"]
    iterations = state["iterations"]

    repo_path_set = set(state["repo_path"])

    prompt = _build_prompt(
        question=state["question"],
        current_target=state["current_target"],
        chunks=chunks,
        findings=findings,
    )

    llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(
        EvaluateChunkOutput
    )
    result: EvaluateChunkOutput = llm.invoke(prompt)

    # Update findings
    updated_findings = list(findings)
    if result.is_relevant:
        for chunk in chunks:
            updated_findings.append(
                Finding(
                    file=chunk["file"],
                    lines=chunk["lines"],
                    note=result.note,
                )
            )

    # Push new targets onto the back of the queue — skip already visited
    visited_set = set(state["visited"])
    current_queue = list(state["search_queue"])
    queued_set = set(current_queue)

    for target in result.next_search_targets:
        if target not in visited_set and target not in queued_set:
            if looks_like_file_path(target):
                if target not in repo_path_set:
                    continue  # skip file paths that aren't actually in the repo
            current_queue.append(target)
            queued_set.add(target)

    # Stop conditions
    new_iterations = iterations + 1
    explore_done = result.done or new_iterations >= MAX_ITERATIONS

    return {
        "findings": updated_findings,
        "search_queue": current_queue,
        "iterations": new_iterations,
        "explore_done": explore_done,
    }


# ─── Prompt builder ───────────────────────────────────────────────────────────


def _build_prompt(
    question: str,
    current_target: str,
    chunks: list,
    findings: list[Finding],
) -> str:

    # Format chunks — cap each one so we don't blow context
    chunks_block = ""
    for chunk in chunks:
        content = chunk["content"]
        if len(content) > MAX_CHUNK_CHARS:
            content = content[:MAX_CHUNK_CHARS] + "\n# ... truncated"
        chunks_block += (
            f"--- File: {chunk['file']} | Lines: {chunk['lines']} ---\n{content}\n\n"
        )

    # TODO: need to improve here, we may summarize findings and then send to llm
    # Condense findings — just file + note, not raw content
    # Full chunk content isn't needed here; the synthesize node doesn't use this prompt
    if findings:
        findings_block = "\n".join(
            f"{i + 1}. {f['file']} (L{f['lines']}): {f['note']}"
            for i, f in enumerate(findings)
        )
    else:
        findings_block = "None yet."

    prompt = f"""
        You are one iteration of a codebase research agent's explore loop.

        RESEARCH QUESTION:
        {question}

        CURRENT SEARCH TARGET:
        {current_target}

        CODE CHUNKS FOUND FOR THIS TARGET:
        {chunks_block}
        FINDINGS ACCUMULATED SO FAR:
        {findings_block}

        Your tasks:
        1. Decide if the chunks above are relevant to the research question.
        2. If relevant, write a concise note explaining what they reveal.
        3. Propose next search targets (symbols, literals) to deepen the answer.
        — Do NOT re-suggest anything already covered in findings so far.
        — Do NOT suggest generic terms like "import" or "class".
        4. Decide if the findings so far are enough to fully answer the question.
        Be conservative — only mark done when the core mechanism is clear, not just hinted at.
        5. For file path targets: ONLY suggest files you have already seen referenced
           in the chunks above or in findings so far. Do not invent file paths.
        """

    return prompt
