"""Basic context gathering: read the repo's small text files up to a size cap.

Week 2 replaces this with a ContextGatherer that picks only files relevant to the task.
"""

from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}
TEXT_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".toml", ".json", ".yaml", ".yml",
    ".txt", ".cfg", ".ini", ".html", ".css", ".sh", ".go", ".rs", ".java", ".rb",
}


def gather_context(
    root: Path, max_file_bytes: int = 30_000, max_total_bytes: int = 200_000
) -> dict[str, str]:
    root = root.resolve()
    files: dict[str, str] = {}
    total = 0
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts) or not path.is_file():
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        size = path.stat().st_size
        if size > max_file_bytes or total + size > max_total_bytes:
            continue
        try:
            files[rel.as_posix()] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        total += size
    return files
