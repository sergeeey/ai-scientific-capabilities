"""Truth-vault checks: hash pin, location outside the repo, tamper refusal, AST whitelist,
and no full law expression in git-tracked files.

Note: the vault must exist for the suite to import aisci.hidden_laws (LAWS is loaded at import).
"""

import hashlib
import json
import os
import subprocess

import pytest

from aisci import hidden_laws

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _vault_file():
    return hidden_laws._vault_path()


def _vault_expressions():
    with open(_vault_file(), encoding="utf-8") as f:
        data = json.load(f)
    return [spec["expr"] for spec in data["laws"].values()]


def test_pinned_hash_matches_vault_file():
    with open(_vault_file(), "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == hidden_laws.TRUTH_SHA256


def test_vault_is_outside_the_repository():
    vault = os.path.abspath(_vault_file())
    assert not vault.startswith(ROOT + os.sep)


def test_tampered_vault_is_refused(tmp_path, monkeypatch):
    with open(_vault_file(), encoding="utf-8") as f:
        data = json.load(f)
    data["laws"]["null"]["expr"] = "1.0 * x[0]"
    bad = tmp_path / "laws.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("AISCI_TRUTH_VAULT", str(bad))
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        hidden_laws._load_laws()


def test_missing_vault_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("AISCI_TRUTH_VAULT", str(tmp_path / "nope.json"))
    with pytest.raises(FileNotFoundError, match="truth vault not found"):
        hidden_laws._load_laws()


@pytest.mark.parametrize(
    "expr",
    [
        "__import__('os').system('echo')",
        "x[0] + open('f')",
        "x.real",
        "x[0] if x[1] else 0",
        "x[0] + y",
        "math.sqrt(x[0])",
        "x['a']",
    ],
)
def test_ast_whitelist_rejects_unsafe_expressions(expr):
    with pytest.raises(ValueError):
        hidden_laws._make_fn(expr)


@pytest.mark.parametrize("expr", ["9 ** 9 ** 9", "x[0] ** 100", "x[0] ** (2 + 0)"])
def test_huge_or_nonliteral_exponents_are_rejected(expr):
    # 9**9**9 would be computed at eval time and hang; the check must fail before compile.
    with pytest.raises(ValueError):
        hidden_laws._make_fn(expr)


def test_syntax_error_does_not_echo_the_expression():
    secret_like = "1.123456 * x[0] +* 7.654321"
    with pytest.raises(ValueError) as info:
        hidden_laws._make_fn(secret_like)
    assert "1.123456" not in str(info.value)
    assert info.value.__cause__ is None


def test_law_repr_hides_terms_and_description():
    law = hidden_laws.LAWS["in_space"]
    text = repr(law)
    assert text == "Law('in_space')"
    for term in law.terms:
        assert term not in text


def test_ast_whitelist_accepts_vault_style_expressions():
    # Different coefficients on purpose: this file must not contain a real law expression.
    f = hidden_laws._make_fn("1.1 * x[0] * x[1] + 0.3 * x[2] ** 2")
    assert abs(f((1.0, 2.0, 2.0)) - 2.2 - 1.2) < 1e-12


def test_full_law_expressions_are_not_in_tracked_files():
    tracked = subprocess.run(
        ["git", "-C", ROOT, "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split()
    exprs = _vault_expressions()
    hits = []
    for rel in tracked:
        if rel.startswith("results/") or rel == "tests/test_truth_vault.py":
            continue
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            continue
        for e in exprs:
            if e and e in text and e != "0.0":
                hits.append((rel, e))
    assert hits == []
