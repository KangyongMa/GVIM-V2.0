#!/usr/bin/env python3
"""Smoke tests for the PDF DFT extractor skill."""

from __future__ import annotations

import sys

try:
    from extract_dft import batch_process, extract_molecules_from_markdown, process_pdf

    print("module import: ok")
except ImportError as exc:
    print(f"module import: failed: {exc}")
    sys.exit(1)


test_md = """
# Computed coordinates

01_test_molecule_b3pw91.log
<table>
<tr><td>C</td><td>0.000000</td><td>0.000000</td><td>0.000000</td></tr>
<tr><td>H</td><td>1.000000</td><td>0.000000</td><td>0.000000</td></tr>
</table>

02_test_molecule_pbe0.log
<table>
<tr><td>O</td><td>0.500000</td><td>0.500000</td><td>0.500000</td></tr>
</table>
"""

molecules = extract_molecules_from_markdown(test_md)
if len(molecules) != 2:
    print(f"coordinate extraction: failed, expected 2 got {len(molecules)}")
    sys.exit(1)

print("coordinate extraction: ok")
print("smoke test: ok")
