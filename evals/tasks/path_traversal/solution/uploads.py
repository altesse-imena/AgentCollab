from pathlib import Path


def read_upload(base_dir: str, filename: str) -> str:
    base = Path(base_dir).resolve()
    target = (base / filename).resolve()
    if not target.is_relative_to(base):
        raise ValueError(f"refusing to read outside {base_dir}")
    return target.read_text()
