def paginate(items, page, size):
    if page < 1 or size < 1:
        raise ValueError("page and size must be at least 1")
    start = (page - 1) * size
    return items[start : start + size]
