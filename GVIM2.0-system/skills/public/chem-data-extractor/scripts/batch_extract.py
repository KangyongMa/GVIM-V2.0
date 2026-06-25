#!/usr/bin/env python3
"""
Batch Chemistry Data Extractor

Process one or more converted Markdown/text files and extract structured
compound characterization data. PDF conversion is intentionally out of scope for
the default GVIM desktop runtime.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt"}


def extract_compounds(document_path: Path) -> list:
    """Extract all compounds from a Markdown/text file."""
    script_dir = Path(__file__).parent
    extract_script = script_dir / "extract_chem_data.py"

    cmd = [
        sys.executable,
        str(extract_script),
        str(document_path),
        "--compact",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[Error] Failed to extract compounds from {document_path}: {result.stderr}")
        return []

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"[Error] Failed to parse JSON: {e}")
        return []


def process_single_document(document_path: Path, output_base: Path) -> dict:
    """Process a single Markdown/text file and save extracted compound data."""
    document_name = document_path.stem
    document_output_dir = output_base / document_name

    result = {
        "document_name": document_path.name,
        "document_path": str(document_path),
        "output_dir": str(document_output_dir),
        "status": "pending",
        "compounds_count": 0,
        "compounds_file": None,
        "errors": [],
    }

    print(f"\n{'=' * 60}")
    print(f"Processing: {document_path.name}")
    print(f"Output folder: {document_output_dir}")
    print(f"{'=' * 60}")

    document_output_dir.mkdir(parents=True, exist_ok=True)

    try:
        compounds = extract_compounds(document_path)
        result["compounds_count"] = len(compounds)

        if not compounds:
            print(f"[Warning] No compounds found in {document_path.name}")
            result["status"] = "warning"
            result["errors"].append("No compounds found")
        else:
            print(f"[Batch] Extracted {len(compounds)} compounds")

        json_file = document_output_dir / "compounds.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(compounds, f, indent=2, ensure_ascii=False)

        result["compounds_file"] = str(json_file)
        result["status"] = "success"
        print(f"[Batch] Saved to: {json_file}")

        summary = {
            "document_name": document_path.name,
            "processed_at": datetime.now().isoformat(),
            "compounds_count": len(compounds),
            "compounds_file": "compounds.json",
            "compound_list": [c.get("compound_name", "Unknown") for c in compounds],
        }

        summary_file = document_output_dir / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
        print(f"[Error] Exception processing {document_path.name}: {e}")

    return result


def collect_documents(input_path: Path) -> list[Path]:
    """Collect supported Markdown/text documents from a file or directory."""
    if input_path.is_file():
        if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValueError(f"Input file must be one of {supported}: {input_path}")
        return [input_path]

    if input_path.is_dir():
        documents = []
        for suffix in SUPPORTED_EXTENSIONS:
            documents.extend(input_path.glob(f"*{suffix}"))
        return sorted(set(documents))

    raise FileNotFoundError(f"Input path does not exist: {input_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch extract chemistry compound data from converted Markdown/text files."
    )
    parser.add_argument("input", help="Input Markdown/text file or directory containing converted documents")
    parser.add_argument(
        "-o",
        "--output",
        default="./chem_extract_output",
        help="Output base directory (default: ./chem_extract_output)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip documents that already have output folders",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_base = Path(args.output)
    output_base.mkdir(parents=True, exist_ok=True)

    try:
        documents = collect_documents(input_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not documents:
        print(f"Error: No supported Markdown/text files found in: {input_path}")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print("Batch Chemistry Data Extractor")
    print(f"{'=' * 60}")
    print(f"Found {len(documents)} document(s)")
    print(f"Output directory: {output_base.absolute()}")
    print(f"{'=' * 60}\n")

    results = []
    for i, document in enumerate(documents, 1):
        print(f"\n[{i}/{len(documents)}] Processing: {document.name}")

        if args.skip_existing:
            expected_output = output_base / document.stem
            if expected_output.exists() and (expected_output / "compounds.json").exists():
                print(f"[Skip] Already processed: {document.name}")
                summary_path = expected_output / "summary.json"
                summary = {}
                if summary_path.exists():
                    with open(summary_path, encoding="utf-8") as f:
                        summary = json.load(f)
                results.append(
                    {
                        "document_name": document.name,
                        "status": "skipped",
                        "compounds_count": summary.get("compounds_count", 0),
                    }
                )
                continue

        result = process_single_document(document, output_base)
        results.append(result)

    batch_summary = {
        "processed_at": datetime.now().isoformat(),
        "total_documents": len(documents),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] in ["failed", "error"]),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "total_compounds": sum(r.get("compounds_count", 0) for r in results),
        "results": results,
    }

    summary_file = output_base / "batch_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(batch_summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print("Batch Processing Complete")
    print(f"{'=' * 60}")
    print(f"Total documents: {batch_summary['total_documents']}")
    print(f"Successful: {batch_summary['successful']}")
    print(f"Failed: {batch_summary['failed']}")
    print(f"Skipped: {batch_summary['skipped']}")
    print(f"Total compounds extracted: {batch_summary['total_compounds']}")
    print(f"Summary file: {summary_file}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
