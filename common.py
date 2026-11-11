"""Files and run identity shared by the eval scripts."""

import hashlib
import json
import os
import platform
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixture.json"
MANIFEST = ROOT / "index.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def credentials():
    values = [os.getenv(k) for k in ("MOSS_PROJECT_ID", "MOSS_PROJECT_KEY")]
    if not all(values):
        raise SystemExit(
            "Set MOSS_PROJECT_ID and MOSS_PROJECT_KEY for your test project."
        )
    return values


def dataset():
    data = read(FIXTURE)
    manifest = read(MANIFEST)
    if (
        manifest["state"] != "ready"
        or manifest["documents"] != digest(data["documents"])
        or manifest["project"] != digest(credentials()[0])
    ):
        raise SystemExit(
            "The index manifest must match the ready fixture and test project."
        )
    doc_ids = {row["id"] for row in data["documents"]}
    cases = data["cases"]
    if not cases or len({row["id"] for row in cases}) != len(cases):
        raise SystemExit("Provide one or more retrieval cases with unique IDs.")
    if any(row["expected"] not in doc_ids for row in cases):
        raise SystemExit("Each expected document ID must occur in the corpus.")
    return data, manifest


def versions():
    return {
        "moss": version("moss"),
        "native_core": version("inferedge-moss-core"),
        "python": platform.python_version(),
    }
