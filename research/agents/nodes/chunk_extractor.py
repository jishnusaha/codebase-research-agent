import ast
import os

from ..data import EXT_TO_LANGUAGE
from ..types import CodeChunk


LINE_WINDOW = 40  # fallback padding lines above/below match
MAX_CHUNK_LINES = 200  # cap on AST node extraction — avoids 500-line class dumps


def extract_chunks(
    repo_path: str,
    ranked_files: list[str],  # absolute paths, ordered by hit count
    hits_by_file: dict[str, list[int]],  # absolute path → matched line numbers
) -> list[CodeChunk]:
    """
    For each file in ranked_files, extract the minimal code chunk(s)
    that contain the matched lines. Returns CodeChunk list ready for
    LLM evaluation.
    """
    chunks: list[CodeChunk] = []

    for abs_path in ranked_files:
        matched_lines = hits_by_file.get(abs_path, [])
        if not matched_lines:
            continue

        ext = os.path.splitext(abs_path)[1].lower()
        language = EXT_TO_LANGUAGE.get(ext)

        if language == "python":
            regions = _python_regions(abs_path, matched_lines)
        else:
            regions = _window_regions(abs_path, matched_lines)

        rel_path = os.path.relpath(abs_path, repo_path)
        for start, end, content in regions:
            chunks.append(
                CodeChunk(
                    file=rel_path,
                    lines=f"{start}-{end}",
                    content=content,
                )
            )

    return chunks


# ─── Python AST extraction ───────────────────────────────────────────────────


def _python_regions(
    file_path: str,
    matched_lines: list[int],
) -> list[tuple[int, int, str]]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        source_lines = source.splitlines()
        tree = ast.parse(source)
    except (SyntaxError, OSError, ValueError):
        # Parser failed — fall back to line-window so we don't lose the hit
        return _window_regions(file_path, matched_lines)

    # TODO: seen should be per file wise, so that we don't re check same code block again
    # seen_chunks: set[tuple[str, int, int]]
    seen: dict[tuple[int, int], str] = {}  # (start, end) → content; dedupes same node

    for line_num in matched_lines:
        node = _find_enclosing_node(tree, line_num)

        if node is None:
            # Module-level match (import, top-level assignment, etc.)
            start = max(1, line_num - 15)
            end = min(len(source_lines), line_num + 15)
        else:
            start = node.lineno
            end = node.end_lineno  # type: ignore[attr-defined]

            if end - start > MAX_CHUNK_LINES:
                # Enclosing node is huge (e.g. a 400-line class) —
                # take a window centered on the match within the node bounds
                half = LINE_WINDOW // 2
                start = max(node.lineno, line_num - half)
                end = min(node.end_lineno, line_num + half)  # type: ignore

        key = (start, end)
        if key not in seen:
            chunk_lines = source_lines[start - 1 : end]
            seen[key] = "\n".join(chunk_lines)

    return [(s, e, content) for (s, e), content in seen.items()]


def _find_enclosing_node(
    tree: ast.AST, line_number: int
) -> ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | None:
    """
    Walk the AST and return the SMALLEST node (function/method/class)
    that contains the given line. 'Smallest' = minimum line span,
    so a method inside a class wins over the class itself.
    """
    best: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | None = None
    best_span = float("inf")

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if not hasattr(node, "end_lineno"):
            continue  # Python <3.8 — shouldn't happen but guard anyway
        if node.lineno <= line_number <= node.end_lineno:  # type: ignore
            span = node.end_lineno - node.lineno  # type: ignore
            if span < best_span:
                best = node
                best_span = span

    return best


# ─── Line-window fallback ────────────────────────────────────────────────────


def _window_regions(
    file_path: str,
    matched_lines: list[int],
    window: int = LINE_WINDOW,
) -> list[tuple[int, int, str]]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source_lines = f.read().splitlines()
    except OSError:
        return []

    total = len(source_lines)

    # Build raw windows then merge overlapping ones — avoids sending
    # the same lines twice when two matches are close together
    raw: list[tuple[int, int]] = []
    for line_num in sorted(matched_lines):
        raw.append((max(1, line_num - window), min(total, line_num + window)))

    merged: list[tuple[int, int]] = []
    for start, end in raw:
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    return [(s, e, "\n".join(source_lines[s - 1 : e])) for s, e in merged]
