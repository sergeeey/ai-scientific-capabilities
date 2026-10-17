"""Provenance: what produced a result. Stdlib only.

Records config, seed, budget, algorithm names, Python/pytest versions, git commit and
dirty state, and SHA-256 of the code and output artifacts. Nothing here is a
claim about the science; it only makes a run traceable.
"""

import hashlib
import importlib.metadata as md
import json
import os
import platform
import subprocess
import sys

PKG_DIR = os.path.join(os.path.dirname(__file__))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def code_hashes():
    out = {}
    for name in sorted(os.listdir(PKG_DIR)):
        if name.endswith(".py"):
            out[f"src/aisci/{name}"] = sha256_file(os.path.join(PKG_DIR, name))
    return out


def git_info(repo_dir):
    try:
        commit = subprocess.run(
            ["git", "-C", repo_dir, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", repo_dir, "status", "--porcelain", "--", "src", "tests", "docs"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return {"commit": commit, "branch_dirty_in_src_tests_docs": bool(status)}
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"commit": None, "error": type(exc).__name__}


def environment_info():
    try:
        pytest_version = md.version("pytest")
    except md.PackageNotFoundError:
        pytest_version = None
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "pytest": pytest_version,
        "third_party_dependencies": [],  # runner is stdlib only
    }


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
