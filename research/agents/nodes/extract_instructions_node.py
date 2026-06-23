from typing import Literal
from urllib.parse import urlparse
from research.agents.types import ResearchAgentState
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class ExtractInstructionsNodeInput(BaseModel):
    repo_url: str = Field(default="", description="Github repository URL")

    question: str = Field(default="", description="Research question")

    is_valid: bool = Field(
        ..., description="True only when both repo_url and question are present"
    )


def _validate_repo_url(repo_url: str) -> bool:
    """Minimal sanity check so we don't shell out to garbage input."""
    try:
        parsed = urlparse(repo_url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and parsed.netloc.endswith("github.com")


def extract_instructions_node(state: ResearchAgentState):

    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0).with_structured_output(
        ExtractInstructionsNodeInput
    )

    prompt = f"""
        You are extracting instructions for a repository research agent.

        User request:

        {state["original_question"]}

        Extract:
        1. GitHub repository URL
        2. Research question

        Rules:
        - repo_url must be a GitHub repository URL.
        - question should be rewritten as a clear research task.
        - If either is missing, return is_valid=False.
    """

    data: ExtractInstructionsNodeInput = llm.invoke(prompt)

    if not data.is_valid:
        return {
            "should_end": True,
            "end_reason": "Missing repo_url or question",
            "response": (
                "Please provide both:\n"
                "1. A GitHub repository URL\n"
                "2. A research question"
            ),
        }

    if not _validate_repo_url(data.repo_url):
        return {
            "should_end": True,
            "end_reason": f"'{data.repo_url}' is not a valid GitHub repository URL.",
            "response": f"'{data.repo_url}' doesn't look like a valid GitHub repository URL.",
        }

    return {
        "repo_url": data.repo_url.replace(".git", "").lower(),
        "question": data.question,
    }
