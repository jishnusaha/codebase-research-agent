import os

from ..data import EXT_TO_LANGUAGE


def looks_like_file_path(target: str) -> bool:
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
