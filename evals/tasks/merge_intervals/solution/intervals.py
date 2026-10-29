def merge_intervals(intervals):
    for start, end in intervals:
        if start > end:
            raise ValueError(f"invalid interval [{start}, {end}]")
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
