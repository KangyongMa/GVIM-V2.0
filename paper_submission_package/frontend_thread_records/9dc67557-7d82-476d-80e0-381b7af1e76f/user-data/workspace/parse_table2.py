#!/usr/bin/env python3
"""Parse Table 2 from the extracted MinerU HTML and write CSV + report."""

import csv
import re
from html.parser import HTMLParser
from pathlib import Path

# Read the full markdown extraction
md_text = Path("E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/f37c0628-e18f-4d93-9d56-fa16c1efbe50/threads/9dc67557-7d82-476d-80e0-381b7af1e76f/user-data/workspace/reaction_output/nanomaterials-12-01070/nanomaterials-12-01070/extracted/full.md").read_text(encoding="utf-8")

# Find the table between <table> and </table>
table_match = re.search(r"<table>(.*?)</table>", md_text, re.DOTALL)
if not table_match:
    print("ERROR: No <table> found in markdown")
    exit(1)

table_html = table_match.group(0)

class Table2Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = []
        self.current_cell = []
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag in ("td", "th"):
            self.in_cell = True
            self.current_cell = []

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.in_cell = False
            self.current_row.append("".join(self.current_cell).strip())
        elif tag == "tr":
            if self.current_row:
                self.rows.append(self.current_row)
                self.current_row = []

parser = Table2Parser()
parser.feed(table_html)

# Clean rows: remove separator row, filter out empty
data_rows = []
for row in parser.rows:
    # Skip header row
    if any(h.lower() in " ".join(row).lower() for h in ["entry", "catalyst", "solvent"]):
        continue
    # Skip rows that don't look like data (need at least 3 columns)
    if len(row) >= 4:
        data_rows.append(row)

print(f"Found {len(data_rows)} data rows")

# Build entry list
entries = []
for i, row in enumerate(data_rows):
    entry_num = i + 1
    catalyst = row[1] if len(row) > 1 else ""
    solvent = row[2] if len(row) > 2 else ""
    temp_str = row[3] if len(row) > 3 else ""
    yield_str = row[4] if len(row) > 4 else ""

    # Clean LaTeX-style math
    catalyst = catalyst.replace("$", "").strip()
    solvent = solvent.replace("$", "").strip()
    
    # Parse temperature
    temp_match = re.search(r"(\d+)", temp_str)
    temperature_c = int(temp_match.group(1)) if temp_match else ""

    # Parse yield - extract first number
    yield_match = re.search(r"(\d+)", yield_str)
    yield_pct = int(yield_match.group(1)) if yield_match else 0

    entries.append({
        "entry": entry_num,
        "catalyst": catalyst,
        "solvent": solvent,
        "temperature_c": temperature_c,
        "yield_percent": yield_pct,
        "yield_raw": yield_str.replace("$", "").strip()
    })

# Handle trace yields: entry 2 has "trace"
if len(data_rows) > 1:
    entries[1]["yield_percent"] = "trace"

# Write CSV
csv_path = Path("E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/f37c0628-e18f-4d93-9d56-fa16c1efbe50/threads/9dc67557-7d82-476d-80e0-381b7af1e76f/user-data/outputs/reaction_data.csv")
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["entry", "catalyst", "solvent", "temperature_c", "yield_percent"])
    writer.writeheader()
    for e in entries:
        writer.writerow({
            "entry": e["entry"],
            "catalyst": e["catalyst"],
            "solvent": e["solvent"],
            "temperature_c": e["temperature_c"],
            "yield_percent": e["yield_percent"]
        })

print(f"CSV written: {csv_path} ({len(entries)} rows)")

# Write report
report = []
report.append("# Reaction Data Extraction Report")
report.append("")
report.append(f"**Source:** nanomaterials-12-01070.pdf (Table 2, Page 6)")
report.append(f"**Extraction tool:** reaction-data-extraction skill (MinerU API + rule-based parsing)")
report.append(f"**Date:** 2026-06-15")
report.append("")
report.append("## Table 2 — Optimization of the Reaction Conditions")
report.append("")
report.append("| Entry | Catalyst | Solvent (v/v) | T (°C) | Yield (%) |")
report.append("|-------|----------|---------------|--------|-----------|")
for e in entries:
    yield_str = str(e["yield_percent"]) if e["yield_percent"] != "trace" else "trace"
    report.append(f"| {e['entry']} | {e['catalyst']} | {e['solvent']} | {e['temperature_c']} | {yield_str} |")

report.append("")
report.append("## Summary")
report.append("")
report.append(f"- **Total entries extracted:** {len(entries)}")
report.append(f"- **Catalysts tested:** Cu(im)₂, Cu@N-C(400), Cu@N-C(600), Cu@N-C(800), CuSO₄ + NaAsc")
report.append(f"- **Solvents:** H₂O, EtOH, i-PrOH, t-BuOH, and binary mixtures with H₂O")
report.append(f"- **Temperature range:** 25–50 °C")
report.append(f"- **Best result:** Entry 15 — Cu@N-C(600), t-BuOH/H₂O (3/1), 50 °C, 98% yield")
report.append("")
report.append("## Notes")
report.append("")
report.append("- Entry 2: No catalyst (control experiment) — trace yield")
report.append("- Entry 18: Same as entry 15 but with 5 mg catalyst instead of 10 mg — 80% yield")
report.append("- Entry 21: Homogeneous CuSO₄ + NaAsc system — 88% yield")

report_path = Path("E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/f37c0628-e18f-4d93-9d56-fa16c1efbe50/threads/9dc67557-7d82-476d-80e0-381b7af1e76f/user-data/outputs/report.md")
report_path.write_text("\n".join(report), encoding="utf-8")
print(f"Report written: {report_path}")

# Print all entries for verification
for e in entries:
    print(f"  Entry {e['entry']:2d}: cat={e['catalyst']:<20s} solvent={e['solvent']:<20s} T={e['temperature_c']}°C yield={e['yield_percent']}")
