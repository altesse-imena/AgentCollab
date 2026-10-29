"""Picks which repo files the agents see.

Small repos are sent whole. When a repo is over the size limit, files are ranked by
relevance to the task (named in the task, imported by those files, their tests, project
docs) and added in that order until the limit is reached.
"""

import re
from pathlib import Path, PurePosixPath

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}
TEXT_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".toml", ".json", ".yaml", ".yml",
    ".txt", ".cfg", ".ini", ".html", ".css", ".sh", ".go", ".rs", ".java", ".rb",
}  # fmt: skip
PROJECT_FILES = {"readme.md", "pyproject.toml", "package.json", "setup.cfg", "requirements.txt"}
IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE)


def read_text_files(root: Path, max_file_bytes: int = 30_000) -> dict[str, str]:
    files = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts) or not path.is_file():
            continue
        if path.suffix not in TEXT_SUFFIXES or path.stat().st_size > max_file_bytes:
            continue
        try:
            files[rel.as_posix()] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    return files


def _module_paths(module: str) -> set[str]:
    base = module.replace(".", "/")
    return {f"{base}.py", f"{base}/__init__.py"}


def rank_files(files: dict[str, str], task: str) -> list[str]:
    words = {w.lower() for w in re.findall(r"[\w.\-/]+", task)}
    named = set()
    for path in files:
        p = PurePosixPath(path)
        if {path.lower(), p.name.lower(), p.stem.lower()} & words:
            named.add(path)
    imported = set()
    for path in named:
        for a, b in IMPORT.findall(files[path]):
            imported |= _module_paths(a or b) & files.keys()
    stems = {PurePosixPath(p).stem for p in named}
    tests = {p for p in files if PurePosixPath(p).stem.removeprefix("test_") in stems} - named

    def score(path: str) -> tuple:
        tier = (
            0 if path in named else
            1 if path in imported else
            2 if path in tests else
            3 if PurePosixPath(path).name.lower() in PROJECT_FILES else
            4
        )  # fmt: skip
        return (tier, len(files[path]), path)  # then smaller files first

    return sorted(files, key=score)


def gather_context(root: Path, task: str = "", max_total_bytes: int = 200_000) -> dict[str, str]:
    files = read_text_files(root.resolve())
    if sum(len(c) for c in files.values()) <= max_total_bytes:
        return files
    chosen, total = {}, 0
    for path in rank_files(files, task):
        size = len(files[path])
        if total + size <= max_total_bytes:
            chosen[path] = files[path]
            total += size
    return chosen
