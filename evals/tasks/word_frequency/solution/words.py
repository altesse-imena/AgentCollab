import re
from collections import Counter


def top_words(text: str, n: int) -> list[tuple[str, int]]:
    if n < 1:
        return []
    counts = Counter(re.findall(r"[a-z']+", text.lower()))
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]
