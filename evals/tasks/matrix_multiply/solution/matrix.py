def _shape(m):
    if not m or not m[0] or any(len(row) != len(m[0]) for row in m):
        raise ValueError("matrix must be non-empty with equal-length rows")
    return len(m), len(m[0])


def matmul(a, b):
    n, k = _shape(a)
    k2, p = _shape(b)
    if k != k2:
        raise ValueError("incompatible shapes")
    return [[sum(a[i][x] * b[x][j] for x in range(k)) for j in range(p)] for i in range(n)]
