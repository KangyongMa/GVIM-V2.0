from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEMOS = [
    ROOT / "demos" / "spectra_to_dihedral.py",
    ROOT / "demos" / "bbbp_property_prediction.py",
    ROOT / "demos" / "bace_active_search.py",
]


def main() -> int:
    summaries = []
    for script in DEMOS:
        print(f"\n=== Running {script.stem} ===", flush=True)
        completed = subprocess.run([sys.executable, str(script)], cwd=ROOT.parent)
        summaries.append({"demo": script.stem, "returncode": completed.returncode})

    failed = [item for item in summaries if item["returncode"] != 0]
    print("\n=== Summary ===")
    print(json.dumps(summaries, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

