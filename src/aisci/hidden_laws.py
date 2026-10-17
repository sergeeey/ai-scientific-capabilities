"""Hidden ground-truth laws. ONLY the runner and checker may import this module.

The laws themselves are NOT in this file or anywhere in the git working tree. They are read
from a vault outside the repository (env var AISCI_TRUTH_VAULT, default: ../aisci-truth-vault
next to the repo). This file pins the SHA-256 of the vault file and refuses to load anything
that does not match. Expressions are parsed with an AST whitelist, so no arbitrary code runs.

Git history before this change still contains the old law text (commits from c49524a
onward). That cannot be undone without rewriting history, which is not done. Blind tests must
therefore use freshly generated laws, not the exp01-exp03 laws.

Each law is a synthetic scenario. These are not physical laws; nothing here is a
discovery claim.
"""

import ast
import hashlib
import json
import math
import os
from dataclasses import dataclass

# Commitment to the truth vault file (public; reveals nothing about the laws).
TRUTH_SHA256 = "acc272f14e1896b3dad4a54997473380a262f16738ae9545b54d02f69d723b12"

_REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DEFAULT_VAULT = os.path.join(os.path.dirname(_REPO_DIR), "aisci-truth-vault", "laws.json")

_ALLOWED_FUNCS = {"tanh", "sin", "cos", "exp"}
_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_ALLOWED_UNARY = (ast.USub, ast.UAdd)
_MAX_EXPONENT = 8
_MAX_EXPR_LEN = 500


@dataclass(frozen=True, repr=False)
class Law:
    name: str
    fn: object
    terms: frozenset  # names of the library terms that realise the law exactly
    description: str

    def __repr__(self):
        # Structure (terms) and description stay out of logs and tracebacks.
        return f"Law({self.name!r})"


def _check(node):
    """Accept only arithmetic over x[i] and whitelisted math functions."""
    if isinstance(node, ast.Expression):
        return _check(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return
    if isinstance(node, ast.Subscript):
        if not (isinstance(node.value, ast.Name) and node.value.id == "x"):
            raise ValueError("only x[i] subscripts are allowed")
        if not (isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int)):
            raise ValueError("subscript must be an integer literal")  # noqa: TRY004 (kept ValueError: tests expect it)
        return
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
        if isinstance(node.op, ast.Pow):
            # Only small literal exponents: a constant like 9**9**9 is computed at eval time
            # and would hang the process. The vault is hash-pinned, but the guard is cheap.
            r = node.right
            if not (
                isinstance(r, ast.Constant)
                and isinstance(r.value, (int, float))
                and abs(r.value) <= _MAX_EXPONENT
            ):
                raise ValueError(f"exponent must be a literal with |e| <= {_MAX_EXPONENT}")
        _check(node.left)
        _check(node.right)
        return
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARY):
        _check(node.operand)
        return
    if isinstance(node, ast.Call):
        f = node.func
        if not (
            isinstance(f, ast.Attribute)
            and isinstance(f.value, ast.Name)
            and f.value.id == "math"
            and f.attr in _ALLOWED_FUNCS
        ):
            raise ValueError("only math.{tanh,sin,cos,exp} calls are allowed")
        if node.keywords or len(node.args) != 1:
            raise ValueError("math functions take exactly one positional argument")
        _check(node.args[0])
        return
    raise ValueError(f"disallowed syntax: {type(node).__name__}")


def _make_fn(expr):
    if len(expr) > _MAX_EXPR_LEN:
        raise ValueError(f"expression longer than {_MAX_EXPR_LEN} characters")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        # SyntaxError carries the source line; drop it so the expression never reaches a traceback.
        raise ValueError("expression has a syntax error") from None
    _check(tree)
    code = compile(tree, "<truth>", "eval")
    # AST is whitelisted above; builtins are removed so only `math` and `x` are visible.
    return lambda x: eval(code, {"__builtins__": {}, "math": math}, {"x": x})


def _vault_path():
    return os.environ.get("AISCI_TRUTH_VAULT", _DEFAULT_VAULT)


def _load_laws():
    path = _vault_path()
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"truth vault not found at {path}; set AISCI_TRUTH_VAULT to the vault file"
        )
    with open(path, "rb") as f:
        raw = f.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != TRUTH_SHA256:
        raise ValueError("truth vault SHA-256 mismatch: refusing to load")
    data = json.loads(raw.decode("utf-8"))
    laws = {}
    for name, spec in data["laws"].items():
        laws[name] = Law(
            name,
            _make_fn(spec["expr"]),
            frozenset(spec["terms"]),
            spec["description"],
        )
    return laws


LAWS = _load_laws()
