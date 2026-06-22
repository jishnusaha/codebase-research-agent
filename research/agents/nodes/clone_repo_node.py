import subprocess
import shutil
import os
from uuid import uuid4
from typing import Literal
from ..types import ResearchAgentState


def _clone_repo(repo_url: str, dest_dir: str) -> None:
    """Shallow clone. Raises subprocess.CalledProcessError on failure."""
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, dest_dir],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )


def clone_repo_node(state: ResearchAgentState):
    repo_url = state["repo_url"]
    cloned_repo_dir = os.getenv("CLONED_REPO_DIR", "cloned_repos") + "/" + str(uuid4())
    if not os.path.exists(cloned_repo_dir):
        os.makedirs(cloned_repo_dir)
    try:
        _clone_repo(repo_url, cloned_repo_dir)
    except subprocess.TimeoutExpired:
        shutil.rmtree(cloned_repo_dir, ignore_errors=True)
        return {
            "should_end": True,
            "end_reason": "Clone timed out after 120s.",
            "response": f"Cloning {repo_url} timed out.",
        }
    except Exception as e:
        shutil.rmtree(cloned_repo_dir, ignore_errors=True)
        return {
            "should_end": True,
            "end_reason": f"Failed to clone {repo_url}: {e.stderr.strip() if e.stderr else e}",
            "response": f"Failed to clone {repo_url}: {e.stderr.strip() if e.stderr else e}",
        }

    return {"repo_path": cloned_repo_dir}


def route_after_clone_repo_node(
    state: ResearchAgentState,
) -> Literal["build_repo_map", "__end__"]:
    if state["should_end"]:
        return "__end__"

    return "build_repo_map"
