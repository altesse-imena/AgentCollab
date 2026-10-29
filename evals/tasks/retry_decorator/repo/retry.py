def retry(times):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            for _ in range(times + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    pass
        return wrapper
    return decorator
