from pathlib import Path

PROMPTS = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def render_files(files: dict[str, str]) -> str:
    return "\n\n".join(f"### {path}\n```\n{body}\n```" for path, body in files.items())


def change_messages(
    prompt: str, task: str, context: dict[str, str], patch: str, changed: dict[str, str]
) -> list[dict]:
    """Messages for agents that inspect a proposed change. Repo context goes first so the
    provider's prompt cache can share it with the other agents in the same round."""
    user = (
        f"# Repository files (before the change)\n\n{render_files(context) or '(empty)'}\n\n"
        f"# Task\n\n{task}\n\n"
        f"# Proposed change (unified diff)\n\n```diff\n{patch}\n```\n\n"
        f"# Changed files after the change\n\n{render_files(changed)}"
    )
    return [{"role": "system", "content": prompt}, {"role": "user", "content": user}]
