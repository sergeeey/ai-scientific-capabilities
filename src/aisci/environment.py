"""Measurement environment: wraps a hidden law with observation noise.

The agent gets an Oracle. It can call measure(x), read the call count, and nothing else.
The law is captured in a closure, not stored as an attribute, so `oracle._law` does not
exist. The budget is a hard cap: measure() raises once it is exhausted.

Isolation is SOFT, not a security boundary. Code running in the same process can still
import aisci.hidden_laws or walk a closure (see tests/test_foundation.py, which records
these residual paths explicitly). Only a process boundary would close them.
"""

import random


class BudgetExceeded(RuntimeError):
    pass


class Oracle:
    def __init__(self, law_fn, sigma, seed, budget=None):
        rng = random.Random(seed)
        state = {"calls": 0}

        def _measure(x):
            if budget is not None and state["calls"] >= budget:
                raise BudgetExceeded(f"measurement budget {budget} exhausted")
            state["calls"] += 1
            return law_fn(x) + rng.gauss(0.0, sigma)

        self._measure = _measure
        self._state = state
        self.budget = budget

    @property
    def calls(self):
        return self._state["calls"]

    def measure(self, x):
        return self._measure(x)
