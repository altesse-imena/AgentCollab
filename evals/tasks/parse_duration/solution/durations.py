import re

PATTERN = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")


def parse_duration(text: str) -> int:
    text = text.strip()
    match = PATTERN.fullmatch(text)
    if not text or not match:
        raise ValueError(f"invalid duration: {text!r}")
    h, m, s = (int(g) if g else 0 for g in match.groups())
    return h * 3600 + m * 60 + s
