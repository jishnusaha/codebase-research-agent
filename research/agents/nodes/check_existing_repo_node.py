import os

from ..types import ResearchAgentState
from ...models import ClonedRepository


def check_existing_repo_node(state: ResearchAgentState):
    repo_url = state["repo_url"]
    cloned_repository = ClonedRepository.objects.filter(repo_url=repo_url)
    # checking if the repo exists in the database
    if not cloned_repository.exists():
        return {"should_clone": True, "should_build_repo_map": True}
    repo = cloned_repository.first()

    cloned_repo_dir = repo.local_path
    # checking if the repo exists in the local filesystem
    if not os.path.exists(cloned_repo_dir) or not os.listdir(cloned_repo_dir):
        return {"should_clone": True, "should_build_repo_map": True}

    # checking if the repo has a repo_map and primary_language
    if repo.repo_map and repo.primary_language:
        return {
            "should_clone": False,  # no need to clone again
            "should_build_repo_map": False,  # already have it, skip
            "repo_path": cloned_repo_dir,
            "repo_map": repo.repo_map,
            "primary_language": repo.primary_language,
        }

    return {
        "should_clone": False,
        "should_build_repo_map": True,  # path exists but map is missing, rebuild it
        "repo_path": cloned_repo_dir,
    }
