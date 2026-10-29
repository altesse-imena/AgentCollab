def remove_expired(sessions: dict, now: float) -> int:
    expired = [key for key, session in sessions.items() if session["expires_at"] <= now]
    for key in expired:
        del sessions[key]
    return len(expired)
