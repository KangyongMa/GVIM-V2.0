#!/usr/bin/env python3
"""Prepare a low-token MinerU reaction-table extraction benchmark."""

from __future__ import annotations

import csv
import json
import shutil
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = ROOT / "Demo-MinerU-Reaction"
RUNTIME_DIR = (
    ROOT
    / "research-demos"
    / "showcase-information-extraction"
    / "runtime"
    / "mineru_reaction_table"
)
SOURCE_DIR = ROOT / "research-demos" / "source-data" / "mineru_reaction_table"

PDF_URL = (
    "https://mdpi-res.com/d_attachment/nanomaterials/nanomaterials-12-01070/"
    "article_deploy/nanomaterials-12-01070.pdf"
)
XML_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9000828/fullTextXML"
TABLE_ID = "nanomaterials-12-01070-t002"

GOLD_FIELDS = [
    "entry",
    "catalyst",
    "solvent",
    "temperature_c",
    "yield_percent",
]


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "GVIM-research-demo/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        destination.write_bytes(response.read())


def cell_text(cell: ET.Element) -> str:
    return " ".join("".join(cell.itertext()).split())


def extract_publisher_gold(xml_path: Path, output_csv: Path) -> int:
    root = ET.parse(xml_path).getroot()
    table_wrap = root.find(f".//table-wrap[@id='{TABLE_ID}']")
    if table_wrap is None:
        raise RuntimeError(f"Publisher table {TABLE_ID!r} was not found")

    table = table_wrap.find("table")
    if table is None:
        raise RuntimeError(f"Publisher table {TABLE_ID!r} has no table element")

    rows = []
    for row in table.findall("./tbody/tr"):
        values = [cell_text(cell) for cell in row.findall("td")]
        if len(values) != 5:
            raise RuntimeError(f"Expected 5 cells, found {len(values)}: {values}")
        rows.append(dict(zip(GOLD_FIELDS, values)))

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=GOLD_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    pdf_source = SOURCE_DIR / "nanomaterials-12-01070.pdf"
    xml_source = SOURCE_DIR / "PMC9000828.xml"
    if not pdf_source.exists():
        download(PDF_URL, pdf_source)
    if not xml_source.exists():
        download(XML_URL, xml_source)

    gold_csv = RUNTIME_DIR / "gold" / "publisher_table2_gold.csv"
    row_count = extract_publisher_gold(xml_source, gold_csv)

    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_source, DEMO_DIR / pdf_source.name)

    manifest = {
        "benchmark": "MinerU reaction-condition table extraction",
        "paper": "MOF-Derived Cu@N-C Catalyst for 1,3-Dipolar Cycloaddition Reaction",
        "doi": "10.3390/nano12071070",
        "license": "CC BY 4.0",
        "input_file": pdf_source.name,
        "target": "Table 2, Optimization of the reaction conditions",
        "page_range": "6-6",
        "expected_rows": row_count,
        "fields": GOLD_FIELDS,
        "gold_source": "Publisher JATS XML distributed by Europe PMC",
        "metrics": [
            "exact-match precision",
            "exact-match recall",
            "exact-match F1",
            "exact-row accuracy",
        ],
    }
    (DEMO_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Prepared {DEMO_DIR}")
    print(f"Publisher-gold rows: {row_count}")
    print(f"Hidden gold: {gold_csv}")


if __name__ == "__main__":
    main()
