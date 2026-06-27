#!/usr/bin/env python3
"""Prepare a low-token MS/MS candidate retrieval demo from MassBank records."""

from __future__ import annotations

import csv
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = ROOT / "Demo-MS2-Retrieval"
RUNTIME_DIR = (
    ROOT
    / "research-demos"
    / "showcase-information-extraction"
    / "runtime"
    / "msms_retrieval"
)
SOURCE_DIR = ROOT / "research-demos" / "source-data" / "msms_retrieval" / "massbank_records"

GITHUB_API = "https://api.github.com/repos/MassBank/MassBank-data/contents/Eawag?per_page=100"
USER_AGENT = "GVIM-msms-retrieval-demo/1.0"
MAX_RECORDS_TO_SCAN = 80
N_QUERIES = 5
MIN_PEAKS = 5


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def list_massbank_urls() -> list[str]:
    data = json.loads(fetch_text(GITHUB_API))
    urls = [item["download_url"] for item in data if item["name"].endswith(".txt")]
    return urls[:MAX_RECORDS_TO_SCAN]


def parse_record(text: str, source_url: str) -> dict[str, Any] | None:
    def first(prefix: str) -> str:
        for line in text.splitlines():
            if line.startswith(prefix):
                return line.split(":", 1)[1].strip()
        return ""

    accession = first("ACCESSION:")
    title = first("RECORD_TITLE:")
    name = first("CH$NAME:")
    inchikey = re.sub(r"^INCHIKEY\s+", "", first("CH$LINK: INCHIKEY"))
    precursor = first("MS$FOCUSED_ION: PRECURSOR_M/Z")
    ion_mode = re.sub(r"^ION_MODE\s+", "", first("AC$MASS_SPECTROMETRY: ION_MODE"))
    instrument_type = first("AC$INSTRUMENT_TYPE:")

    peaks: list[tuple[float, float]] = []
    in_peaks = False
    for line in text.splitlines():
        if line.startswith("PK$PEAK:"):
            in_peaks = True
            continue
        if in_peaks:
            if line.startswith("//"):
                break
            parts = line.split()
            if len(parts) >= 2 and re.match(r"^\d", parts[0]):
                try:
                    mz = float(parts[0])
                    intensity = float(parts[-1])
                except ValueError:
                    continue
                peaks.append((mz, intensity))

    precursor_match = re.search(r"(\d+(?:\.\d+)?)", precursor)
    if not accession or not inchikey or not precursor_match or len(peaks) < MIN_PEAKS:
        return None

    return {
        "accession": accession,
        "title": title,
        "name": name or title.split(";")[0],
        "inchikey": inchikey,
        "precursor_mz": float(precursor_match.group(1)),
        "ion_mode": ion_mode,
        "instrument_type": instrument_type,
        "peaks": peaks,
        "source_url": source_url,
    }


def mgf_block(record: dict[str, Any], spectrum_id: str) -> str:
    lines = [
        "BEGIN IONS",
        f"TITLE={spectrum_id}",
        f"SCANS={spectrum_id}",
        f"ACCESSION={record['accession']}",
        f"COMPOUND_NAME={record['name']}",
        f"INCHIKEY={record['inchikey']}",
        f"PEPMASS={record['precursor_mz']:.6f}",
        "CHARGE=1+",
        f"IONMODE={record['ion_mode']}",
    ]
    lines.extend(f"{mz:.6f} {intensity:.6f}" for mz, intensity in record["peaks"])
    lines.append("END IONS")
    return "\n".join(lines)


def write_mgf(records: list[tuple[str, dict[str, Any]]], path: Path) -> None:
    path.write_text("\n\n".join(mgf_block(record, sid) for sid, record in records) + "\n", encoding="utf-8")


def main() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for url in list_massbank_urls():
        filename = SOURCE_DIR / url.rsplit("/", 1)[-1]
        if not filename.exists():
            filename.write_text(fetch_text(url), encoding="utf-8")
        record = parse_record(filename.read_text(encoding="utf-8", errors="replace"), url)
        if record:
            records.append(record)

    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_key[record["inchikey"]].append(record)

    pairs = []
    for inchikey, group in by_key.items():
        if len(group) >= 2:
            group = sorted(group, key=lambda item: item["accession"])
            pairs.append((inchikey, group[0], group[1]))
    pairs = pairs[:N_QUERIES]
    if len(pairs) < N_QUERIES:
        raise RuntimeError(f"Only found {len(pairs)} reusable MassBank compound groups")

    query_records = [(f"query_{idx+1}", query) for idx, (_, query, _) in enumerate(pairs)]
    library_records = [(f"candidate_{idx+1}_true", reference) for idx, (_, _, reference) in enumerate(pairs)]

    used_accessions = {record["accession"] for _, record in query_records + library_records}
    decoys = [record for record in records if record["accession"] not in used_accessions]
    for idx, record in enumerate(decoys[:10], start=1):
        library_records.append((f"candidate_decoy_{idx}", record))

    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    write_mgf(query_records, DEMO_DIR / "query_spectra.mgf")
    write_mgf(library_records, DEMO_DIR / "reference_library.mgf")

    gold_rows = []
    for idx, (inchikey, query, reference) in enumerate(pairs, start=1):
        gold_rows.append(
            {
                "query_id": f"query_{idx}",
                "query_accession": query["accession"],
                "true_reference_accession": reference["accession"],
                "inchikey": inchikey,
                "compound_name": query["name"],
            }
        )
    gold_path = RUNTIME_DIR / "gold" / "gold_matches.csv"
    gold_path.parent.mkdir(parents=True, exist_ok=True)
    with gold_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(gold_rows[0]))
        writer.writeheader()
        writer.writerows(gold_rows)

    manifest = {
        "benchmark": "MassBank MS/MS candidate retrieval mini-benchmark",
        "source": "MassBank-data Eawag records",
        "source_api": GITHUB_API,
        "query_file": "query_spectra.mgf",
        "library_file": "reference_library.mgf",
        "n_queries": len(query_records),
        "n_library_spectra": len(library_records),
        "gold_rule": "A hit is correct when the ranked candidate has the same MassBank InChIKey as the query.",
        "recommended_similarity": "normalized peak cosine with 0.1 Da fragment m/z tolerance",
        "metrics": ["top-1 accuracy", "top-3 accuracy", "top-5 accuracy", "MRR"],
    }
    (DEMO_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Prepared {DEMO_DIR}")
    print(f"Queries: {len(query_records)}")
    print(f"Library spectra: {len(library_records)}")
    print(f"Gold: {gold_path}")


if __name__ == "__main__":
    main()
