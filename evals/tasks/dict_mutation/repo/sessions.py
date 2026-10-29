def remove_expired(sessions: dict, now: float) -> int:
    removed = 0
    for key, session in sessions.items():
        if session["expires_at"] <= now:
            del sessions[key]
            removed += 1
    return removed
