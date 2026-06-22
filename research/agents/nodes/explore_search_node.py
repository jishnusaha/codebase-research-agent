from collections import defaultdict
import os
import json
import subprocess
from typing import Literal

from ..data import EXT_TO_LANGUAGE, SKIP_DIRS
from ..types import CodeChunk, ResearchAgentState

from .chunk_extractor import extract_chunks


TOP_FILES = 5  # max files to extract chunks from per target
RIPGREP_MAX_MATCHES = 10  # per-file match cap passed to rg --max-count


# ----- Node: explore_search_node -----


def explore_search_node(state: ResearchAgentState) -> dict:
    repo_path = state["repo_path"]
    search_queue = list(state["search_queue"])  # local copy — we mutate it
    visited_set = set(state["visited"])
    visited_list = list(state["visited"])

    while search_queue:
        target = search_queue.pop(0)

        if target in visited_set:
            continue

        # Mark visited immediately — even if grep returns 0 hits.
        # We never want to retry a failed target in the same run.
        visited_set.add(target)
        visited_list.append(target)

        if _looks_like_file_path(target):
            chunks = _chunks_from_file_path(repo_path, target)
        else:
            hits = _run_ripgrep(repo_path, target)
            if not hits:
                continue  # no hits for this target — try next one in queue
            ranked_files, hits_by_file = _rank_files(hits)
            chunks = extract_chunks(repo_path, ranked_files[:TOP_FILES], hits_by_file)

        if chunks:
            return {
                "current_target": target,
                "current_chunks": chunks,
                "search_queue": search_queue,
                "visited": visited_list,
                "explore_done": False,
            }

    # Queue fully exhausted — signal the router to skip evaluate and synthesize
    return {
        "search_queue": [],
        "visited": visited_list,
        "current_target": "",
        "current_chunks": [],
        "explore_done": True,
    }


# ----- Ripgrep search handling ───────────────────────────────────────────────


def _run_ripgrep(repo_path: str, target: str) -> list[dict]:
    """
    Run ripgrep and return a flat list of hit dicts:
      { "file": <abs_path>, "line_number": int, "text": str }

    Uses --json for structured output, --fixed-strings to treat the target
    as a literal (not a regex) — avoids accidental regex metachar explosions
    on symbol names like "solve_dependencies" or "$inject".
    """
    try:
        # TODO: exclude import lines
        result = subprocess.run(
            [
                "rg",
                "--json",
                "--fixed-strings",
                "--max-count",
                str(RIPGREP_MAX_MATCHES),
                target,
                repo_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        # rg not installed — fall back to Python grep
        return _python_grep(repo_path, target)
    except subprocess.TimeoutExpired:
        return []

    hits = []
    for line in result.stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "match":
            continue
        try:
            data = obj["data"]
            hits.append(
                {
                    "file": data["path"]["text"],  # absolute path from rg
                    "line_number": data["line_number"],
                    "text": data["lines"]["text"].rstrip("\n"),
                }
            )
        except KeyError:
            continue

    return hits


def _python_grep(repo_path: str, target: str) -> list[dict]:
    """
    Pure-Python fallback for when ripgrep isn't installed.
    Slower but avoids a hard dependency.
    """
    hits = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in EXT_TO_LANGUAGE:
                continue
            abs_path = os.path.join(dirpath, filename)
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    # TODO: exclude import lines
                    for line_num, line in enumerate(f, start=1):
                        if target in line:
                            hits.append(
                                {
                                    "file": abs_path,
                                    "line_number": line_num,
                                    "text": line.rstrip("\n"),
                                }
                            )
                            if len(hits) >= RIPGREP_MAX_MATCHES * 50:
                                return hits  # safety cap
            except OSError:
                continue
    return hits


# ─── File-path target handling ────────────────────────────────────────────────


def _looks_like_file_path(target: str) -> bool:
    """
    Heuristic: does this target look like a path rather than a symbol?
    Triggers on path separators OR a known code extension with no spaces.
    """
    if " " in target:
        return False
    if "/" in target or os.sep in target:
        return True
    ext = os.path.splitext(target)[1].lower()
    return bool(ext and ext in EXT_TO_LANGUAGE)


def _chunks_from_file_path(repo_path: str, target: str) -> list[CodeChunk]:
    """
    For file-path targets (e.g. 'auth/backends.py'), read the whole file.
    Cap content so we don't blow the evaluate node's context window.
    The evaluate LLM call will receive this as one chunk and can ask for
    specific sub-sections via next_search_targets if needed.
    """
    abs_path = os.path.join(repo_path, target)
    if not os.path.isfile(abs_path):
        return []
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError:
        return []

    # If file is short enough, return whole thing; otherwise first N lines
    # with a note that it was truncated — evaluate node can follow up
    MAX_LINES = 200
    content_lines = lines[:MAX_LINES]
    content = "".join(content_lines).rstrip()
    truncated = len(lines) > MAX_LINES

    if truncated:
        content += f"\n\n# ... file truncated at line {MAX_LINES} of {len(lines)} total"

    return [
        CodeChunk(
            file=target,
            lines=f"1-{min(len(lines), MAX_LINES)}",
            content=content,
        )
    ]


# ─── File ranking ─────────────────────────────────────────────────────────────


def _rank_files(
    hits: list[dict],
) -> tuple[list[str], dict[str, list[int]]]:
    """
    Returns (ranked_abs_paths, hits_by_file).
    Ranked descending by hit count — most-mentioned file first.
    """
    hits_by_file: dict[str, list[int]] = defaultdict(list)
    for hit in hits:
        hits_by_file[hit["file"]].append(hit["line_number"])

    ranked = sorted(
        hits_by_file.keys(), key=lambda f: len(hits_by_file[f]), reverse=True
    )
    return ranked, dict(hits_by_file)
