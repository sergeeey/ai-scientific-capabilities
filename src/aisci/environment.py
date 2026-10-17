"""Measurement environment: wraps a hidden law with observation noise.

The agent gets an Oracle. It can call measure(x) and read the call count; it cannot
read the law. The law itself is passed in by the runner, never imported by agents.
"""

import random


class Oracle:
    def __init__(self, law_fn, sigma, seed):
        self._law = law_fn
        self._sigma = sigma
        self._rng = random.Random(seed)
        self.calls = 0

    def measure(self, x):
        self.calls += 1
        return self._law(x) + self._rng.gauss(0.0, self._sigma)
