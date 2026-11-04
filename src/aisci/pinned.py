"""Pinned artifacts and artifact-level evidence entries. Stdlib only.

A pinned JSON file is one whose SHA-256 is recorded in code (or in a pre-registration).
Thresholds for a test run are read from such a file, never from memory, and the hash is
checked before use. Artifact entries link each derived number to the file it came from.
"""

import hashlib
import json
import os


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def load_pinned_json(path, expected_sha256):
    with open(path, "rb") as f:
        raw = f.read()
    digest = sha256_bytes(raw)
    if digest != expected_sha256:
        raise ValueError(f"pinned file {os.path.basename(path)}: SHA-256 mismatch")
    return json.loads(raw.decode("utf-8"))


def artifact_ledger(out_dir, prefix, files, derived):
    """Write <out_dir>/ledger.jsonl: one 'artifact' entry per file, one 'derived' per number.

    derived: list of (metric, value, source_file) where source_file is one of `files`.
    Every derived entry names the artifact id it was read from, so a claim can be traced to a
    file and its hash.
    """
    entries = []
    ids = {}
    for i, name in enumerate(files, start=1):
        eid = f"{prefix}-A-{i:02d}"
        ids[name] = eid
        with open(os.path.join(out_dir, name), "rb") as f:
            digest = sha256_bytes(f.read())
        entries.append({"id": eid, "type": "artifact", "path": name, "sha256": digest})
    for k, (metric, value, source) in enumerate(derived, start=1):
        entries.append(
            {
                "id": f"{prefix}-D-{k:03d}",
                "type": "derived",
                "metric": metric,
                "value": value,
                "source_artifact": ids[source],
            }
        )
    path = os.path.join(out_dir, "ledger.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in entries)
    return path
