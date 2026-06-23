import os
from typing import Counter

from ..data import EXT_TO_LANGUAGE, SKIP_DIRS
from ..types import RepoFileInfo, ResearchAgentState
from ...models import ClonedRepository

# Cap how much we read per file when sniffing for a leading docstring/comment
DOCSTRING_PEEK_BYTES = 2000


def _extract_leading_comment(file_path: str) -> str | None:
    """
    Cheap, language-agnostic peek at the start of a file to grab an
    orientation comment/docstring. Not a parser — just a heuristic
    for the repo map. AST-based extraction happens later, per-chunk,
    in the explore loop (Step 2d), not here.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(DOCSTRING_PEEK_BYTES)
    except OSError:
        return None

    stripped = head.lstrip()
    if not stripped:
        return None

    # Python/most-scripting triple-quoted docstring
    for quote in ('"""', "'''"):
        if stripped.startswith(quote):
            end = stripped.find(quote, len(quote))
            if end != -1:
                return stripped[len(quote) : end].strip()[:300]

    # Leading // or # comment block (JS/TS/Go/Rust/C-family, Python single-line, etc.)
    lines = stripped.splitlines()
    comment_lines = []
    for line in lines:
        s = line.strip()
        if s.startswith("//") or s.startswith("#"):
            comment_lines.append(s.lstrip("/#").strip())
        elif s == "" and comment_lines:
            continue
        else:
            break
    if comment_lines:
        return " ".join(comment_lines)[:300]

    return None


def build_repo_map(state: ResearchAgentState):
    repo_path = state["repo_path"]
    repo_map: list[RepoFileInfo] = []
    language_counts: Counter[str] = Counter()
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, repo_path)

            try:
                size = os.path.getsize(full_path)
            except OSError:
                continue

            ext = os.path.splitext(filename)[1].lower()
            language = EXT_TO_LANGUAGE.get(ext)
            if language:
                language_counts[language] += 1

            docstring = None
            # Only bother peeking at files we can actually map to a language
            # and that are small-ish text files (skip huge generated assets).
            if language and size <= 1_000_000:
                docstring = _extract_leading_comment(full_path)

            repo_map.append(
                RepoFileInfo(
                    path=rel_path,
                    size=size,
                    language=language,
                    docstring=docstring,
                )
            )
    primary_language = language_counts.most_common(1)[0][0] if language_counts else None

    ClonedRepository.objects.filter(repo_url=state["repo_url"]).update(
        repo_map=repo_map,
        primary_language=primary_language,
    )

    return {
        "repo_map": repo_map,
        "primary_language": primary_language,
    }
