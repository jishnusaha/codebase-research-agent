from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from ..types import ResearchAgentState, Finding

MAX_FINDINGS_CHARS = 8000  # cap total findings sent to synthesize prompt


class Citation(BaseModel):
    file: str
    lines: str
    explanation: str


class SynthesizeOutput(BaseModel):
    summary: str = Field(
        description="One short paragraph — the direct answer to the research question."
    )
    mechanism_explanation: str = Field(
        description=(
            "A detailed explanation of how the code works to produce this answer. "
            "Reference specific functions, classes, and flow — not vague descriptions."
        )
    )
    citations: list[Citation] = Field(
        description="Every file/line range that supports the explanation."
    )


def synthesize_output_node(state: ResearchAgentState) -> dict:
    findings = state["findings"]

    if not findings:
        return {
            "response": (
                "The agent could not find relevant code to answer the question.\n"
                "Try rephrasing or providing a more specific question."
            )
        }

    prompt = _build_prompt(state["question"], findings)

    llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(
        SynthesizeOutput
    )
    result: SynthesizeOutput = llm.invoke(prompt)

    return {"response": _format_response(result)}


# ─── Prompt builder ───────────────────────────────────────────────────────────


def _build_prompt(question: str, findings: list[Finding]) -> str:
    findings_block = _format_findings(findings)

    return f"""
        You are the final synthesis step of a codebase research agent.

        RESEARCH QUESTION:
        {question}

        RELEVANT FINDINGS FROM CODEBASE EXPLORATION:
        {findings_block}

        Your tasks:
        1. Write a direct, concise summary answering the research question.
        2. Write a detailed mechanism explanation — how the code actually works.
        Reference specific function/class names and trace the flow.
        Do not be vague. The reader wants to understand the implementation.
        3. List every citation (file + line range) that supports your explanation.
        Only cite findings listed above — do not invent file paths or line numbers.

        The audience is a software engineer reading an unfamiliar codebase.
        Prioritize precision and specificity over completeness.
    """


def _format_findings(findings: list[Finding]) -> str:
    lines = []
    total_chars = 0

    for i, f in enumerate(findings):
        entry = (
            f"{i + 1}. File: {f['file']} | Lines: {f['lines']}\n   Note: {f['note']}"
        )
        total_chars += len(entry)
        if total_chars > MAX_FINDINGS_CHARS:
            lines.append(f"... ({len(findings) - i} more findings truncated)")
            break
        lines.append(entry)

    return "\n\n".join(lines)


# ─── Response formatter ───────────────────────────────────────────────────────


def _format_response(result: SynthesizeOutput) -> str:
    citations_block = "\n".join(
        f"  • {c.file} (L{c.lines}): {c.explanation}" for c in result.citations
    )

    return (
        f"## Summary\n{result.summary}\n\n"
        f"## How It Works\n{result.mechanism_explanation}\n\n"
        f"## Citations\n{citations_block}"
    )
