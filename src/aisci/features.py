"""Feature libraries available to the research agent.

Agent-side module: it must NOT import the hidden laws (see tests/test_isolation.py).
"""

import math

# Fixed base hypothesis space H0: terms the agent is allowed to combine.
BASE_LIB = {
    "x1": lambda x: x[0],
    "x2": lambda x: x[1],
    "x3": lambda x: x[2],
    "x1*x2": lambda x: x[0] * x[1],
    "x1*x3": lambda x: x[0] * x[2],
    "x2*x3": lambda x: x[1] * x[2],
    "x1^2": lambda x: x[0] ** 2,
    "x2^2": lambda x: x[1] ** 2,
    "x3^2": lambda x: x[2] ** 2,
    "sin(x1)": lambda x: math.sin(x[0]),
    "sin(x2)": lambda x: math.sin(x[1]),
    "sin(x3)": lambda x: math.sin(x[2]),
}

# Pre-specified expansion operators. This is NOT an open-ended language: it is a
# fixed second library that the expansion mechanism switches on when H0 fails.
EXPANSION_LIB = {
    "tanh(x1)": lambda x: math.tanh(x[0]),
    "tanh(x2)": lambda x: math.tanh(x[1]),
    "tanh(x3)": lambda x: math.tanh(x[2]),
    "tanh(x1)*x2": lambda x: math.tanh(x[0]) * x[1],
    "tanh(x1)*x3": lambda x: math.tanh(x[0]) * x[2],
    "tanh(x2)*x1": lambda x: math.tanh(x[1]) * x[0],
    "tanh(x2)*x3": lambda x: math.tanh(x[1]) * x[2],
    "tanh(x3)*x1": lambda x: math.tanh(x[2]) * x[0],
    "tanh(x3)*x2": lambda x: math.tanh(x[2]) * x[1],
}

FULL_LIB = {**BASE_LIB, **EXPANSION_LIB}

# Public domain of the inputs (stated to the agent; the law is not).
BOUNDS = (-2.0, 2.0)
DIM = 3
