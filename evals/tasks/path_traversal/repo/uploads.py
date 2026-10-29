import os


def read_upload(base_dir: str, filename: str) -> str:
    with open(os.path.join(base_dir, filename)) as f:
        return f.read()
