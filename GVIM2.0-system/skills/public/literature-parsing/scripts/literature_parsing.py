#!/usr/bin/env python3
"""Convert a literature PDF to Markdown through MinerU API."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def _load_shared_client() -> None:
    for parent in Path(__file__).resolve().parents:
        shared_dir = parent / "_gvim_shared"
        if shared_dir.exists():
            sys.path.insert(0, str(shared_dir))
            return


_load_shared_client()
from mineru_api import parse_pdf_with_mineru_api  # noqa: E402


def run_mineru(
    input_pdf: str,
    output_dir: str,
    method: str = "auto",
    lang: str = "ch",
    device: str = "cpu",
) -> Dict[str, Any]:
    """Run MinerU through the cloud API and return local output paths."""

    input_path = Path(input_pdf).expanduser().resolve()
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Parsing PDF with MinerU API: {input_path.name}")
    print(f"  output: {output_path}")
    print(f"  language: {lang}")
    if device != "cpu":
        print("  note: --device is ignored in API mode")

    result = parse_pdf_with_mineru_api(
        input_path,
        output_path,
        language=lang,
        is_ocr=(method == "ocr"),
        enable_table=True,
        enable_formula=True,
    )

    if not result.get("success"):
        print(f"MinerU API failed: {result.get('error')}")
        return result

    print(f"MinerU API completed: {result.get('markdown_file')}")
    return result


def organize_output(result: Dict[str, Any], final_output_dir: str) -> Dict[str, Any]:
    """Copy MinerU output files to the final skill output directory."""

    if not result.get("success"):
        return result

    final_path = Path(final_output_dir).expanduser().resolve()
    final_path.mkdir(parents=True, exist_ok=True)

    md_src = Path(result["markdown_file"])
    md_dst = final_path / md_src.name
    shutil.copy2(md_src, md_dst)

    images_final = final_path / "images"
    images_count = int(result.get("images_count") or 0)
    if result.get("images_dir") and Path(result["images_dir"]).exists():
        if images_final.exists():
            shutil.rmtree(images_final)
        shutil.copytree(result["images_dir"], images_final)
    else:
        images_final = None

    metadata = {
        "input_file": result.get("input_file"),
        "output_dir": str(final_path),
        "markdown_file": str(md_dst),
        "images_count": images_count,
        "converted_at": datetime.now().isoformat(),
        "tool": "MinerU API",
        "mode": result.get("mode"),
        "task_id": result.get("task_id"),
        "batch_id": result.get("batch_id"),
    }

    meta_file = final_path / f"{md_src.stem}_metadata.json"
    meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "success": True,
        "output_dir": str(final_path),
        "markdown_file": str(md_dst),
        "images_dir": str(images_final) if images_final else None,
        "metadata_file": str(meta_file),
        **metadata,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a PDF literature file to Markdown using MinerU API."
    )
    parser.add_argument("-i", "--input", required=True, help="Input PDF path")
    parser.add_argument(
        "-o",
        "--output",
        default="~/.openclaw/media/literature-parsing",
        help="Output directory",
    )
    parser.add_argument(
        "-m",
        "--method",
        choices=["auto", "txt", "ocr"],
        default="auto",
        help="Parsing mode. In API mode, only ocr toggles MinerU OCR.",
    )
    parser.add_argument("-l", "--lang", default="ch", help="Document language")
    parser.add_argument(
        "-d",
        "--device",
        choices=["cpu", "cuda"],
        default="cpu",
        help="Kept for compatibility; ignored in API mode.",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Print final JSON")

    args = parser.parse_args()

    input_file = Path(os.path.expanduser(args.input))
    output_dir = Path(os.path.expanduser(args.output))
    if not input_file.exists():
        print(f"Input file does not exist: {input_file}")
        sys.exit(1)

    temp_output = output_dir / "temp"
    result = run_mineru(
        str(input_file),
        str(temp_output),
        method=args.method,
        lang=args.lang,
        device=args.device,
    )
    if not result.get("success"):
        sys.exit(1)

    final_output = output_dir / input_file.stem
    final_result = organize_output(result, str(final_output))
    if temp_output.exists():
        shutil.rmtree(temp_output)

    if not final_result.get("success"):
        print("Failed to organize output.")
        sys.exit(1)

    print("Conversion complete.")
    print(f"Markdown: {final_result['markdown_file']}")
    if final_result.get("images_dir"):
        print(f"Images: {final_result['images_dir']} ({final_result['images_count']})")
    print(f"Metadata: {final_result['metadata_file']}")

    if args.quiet:
        print(json.dumps(final_result, ensure_ascii=False))


if __name__ == "__main__":
    main()
