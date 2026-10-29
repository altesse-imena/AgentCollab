import re

RESERVED = {"admin", "root", "support"}
PATTERN = re.compile(r"[A-Za-z](?:[A-Za-z0-9]|[_-](?=[A-Za-z0-9]))*")


def validate_username(name: str) -> str:
    if not 3 <= len(name) <= 20:
        raise ValueError("username must be 3 to 20 characters")
    if not PATTERN.fullmatch(name):
        raise ValueError("username has invalid characters or separators")
    if name.lower() in RESERVED:
        raise ValueError("username is reserved")
    return name.lower()
