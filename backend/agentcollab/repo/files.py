import difflib
from pathlib import Path, PurePosixPath


class UnsafePath(ValueError):
    pass


def safe_path(root: Path, rel: str) -> Path:
    """Resolve a model-supplied path, refusing anything that escapes the repo."""
    p = PurePosixPath(rel)
    if p.is_absolute() or ".." in p.parts or not p.parts or ".git" in p.parts:
        raise UnsafePath(f"refusing path {rel!r}")
    full = (root / p).resolve()
    if not full.is_relative_to(root.resolve()):
        raise UnsafePath(f"refusing path {rel!r}")
    return full


def make_patch(old: dict[str, str], new: dict[str, str]) -> str:
    """Unified diff between old file contents and the model's new contents."""
    chunks = []
    for path in sorted(new):
        before = old.get(path)
        chunks.extend(
            difflib.unified_diff(
                (before or "").splitlines(keepends=True),
                new[path].splitlines(keepends=True),
                fromfile="/dev/null" if before is None else f"a/{path}",
                tofile=f"b/{path}",
            )
        )
    return "".join(chunks)


def apply_files(root: Path, new: dict[str, str]) -> None:
    for rel, content in new.items():
        target = safe_path(root, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
