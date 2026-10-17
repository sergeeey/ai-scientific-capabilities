"""Hidden ground-truth laws. ONLY the runner and checker may import this module.

Each law is a synthetic scenario. These are not physical laws; nothing here is a
discovery claim.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Law:
    name: str
    fn: object
    terms: frozenset  # names of the library terms that realise the law exactly
    description: str


LAWS = {
    "in_space": Law(
        "in_space",
        lambda x: 1.5 * x[0] * x[1] - 0.8 * x[2] ** 2,
        frozenset({"x1*x2", "x3^2"}),
        "Law expressible in the base space H0.",
    ),
    "needs_expansion": Law(
        "needs_expansion",
        lambda x: 2.0 * math.tanh(x[0]) * x[1] + 0.5 * x[2],
        frozenset({"tanh(x1)*x2", "x3"}),
        "Law outside H0 (tanh not in base space); reachable only via expansion.",
    ),
    "null": Law(
        "null",
        lambda x: 0.0,
        frozenset(),
        "No law: pure observation noise. Any selected term is a false discovery.",
    ),
}
