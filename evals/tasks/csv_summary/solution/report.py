import csv
import io


def column_means(csv_text: str) -> dict[str, float]:
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    if not rows:
        return {}
    means = {}
    for col in rows[0]:
        values = [r[col] for r in rows if r[col] not in (None, "")]
        try:
            numbers = [float(v) for v in values]
        except ValueError:
            continue
        if numbers:
            means[col] = round(sum(numbers) / len(numbers), 2)
    return means
