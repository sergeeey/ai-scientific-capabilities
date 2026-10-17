"""Least-squares model search over subsets of a feature library (stdlib only).

Agent-side module: must not import hidden laws.
"""

import itertools
import math
from dataclasses import dataclass


def lstsq(cols, y):
    """Least squares for columns `cols` (list of length-n lists). Returns (coefs, rss)."""
    k = len(cols)
    A = [[sum(a * c for a, c in zip(cols[i], cols[j])) for j in range(k)] for i in range(k)]
    b = [sum(c * v for c, v in zip(cols[i], y)) for i in range(k)]
    for i in range(k):
        A[i][i] += 1e-9  # tiny ridge for numerical safety
    M = [A[i] + [b[i]] for i in range(k)]
    for col in range(k):
        piv = max(range(col, k), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        p = M[col][col]
        if abs(p) < 1e-15:
            continue
        for r in range(k):
            if r != col and M[r][col] != 0.0:
                f = M[r][col] / p
                for c in range(col, k + 1):
                    M[r][c] -= f * M[col][c]
    coefs = [M[i][k] / M[i][i] if abs(M[i][i]) > 1e-15 else 0.0 for i in range(k)]
    rss = sum((yy - sum(c * col[t] for c, col in zip(coefs, cols))) ** 2 for t, yy in enumerate(y))
    return coefs, rss


def bic(rss, n, k):
    return n * math.log(max(rss / n, 1e-12)) + k * math.log(n)


@dataclass
class Model:
    names: tuple  # chosen library terms (intercept is always included)
    coefs: list  # [intercept, coef_term1, ...]
    terms: tuple  # the (name, fn) pairs, in the order of `names`
    bic: float
    rmse: float  # in-sample RMSE

    def predict(self, x):
        return self.coefs[0] + sum(c * fn(x) for c, (_, fn) in zip(self.coefs[1:], self.terms))


def fit_all(X, y, lib, k=2):
    """All models with at most k library terms plus an intercept, sorted by BIC."""
    n = len(y)
    ones = [1.0] * n
    feats = {name: [fn(x) for x in X] for name, fn in lib.items()}
    out = []
    for size in range(k + 1):
        for combo in itertools.combinations(lib, size):
            cols = [ones] + [feats[c] for c in combo]
            coefs, rss = lstsq(cols, y)
            out.append(
                Model(
                    names=combo,
                    coefs=coefs,
                    terms=tuple((c, lib[c]) for c in combo),
                    bic=bic(rss, n, len(cols)),
                    rmse=math.sqrt(rss / n),
                )
            )
    out.sort(key=lambda m: m.bic)
    return out
