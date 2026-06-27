from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_manifest_has_complete_chains() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["demos"]) >= 3
    for demo in manifest["demos"]:
        assert demo["problem"]
        assert demo["input"]
        assert demo["workflow"]
        assert demo["output"]
        assert demo["metrics"]

