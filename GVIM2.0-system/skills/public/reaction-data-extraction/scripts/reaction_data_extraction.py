#!/usr/bin/env python3
"""Extract reaction tables and conditions from chemistry PDFs."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List


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
    lang: str = "en",
    device: str = "cpu",
    page_range: str | None = None,
) -> Dict[str, Any]:
    """Parse a PDF through MinerU API and return Markdown text/tables."""

    input_path = Path(input_pdf).expanduser().resolve()
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    print("  [1/3] Parsing PDF with MinerU API...")
    print(f"    file: {input_path.name}")
    if device != "cpu":
        print("    note: --device is ignored in API mode")

    result = parse_pdf_with_mineru_api(
        input_path,
        output_path,
        language=lang,
        page_range=page_range,
        enable_table=True,
        is_ocr=(method == "ocr"),
        enable_formula=True,
    )
    if not result.get("success"):
        return result

    text_content = result.get("text_content")
    if not text_content:
        text_content = Path(result["markdown_file"]).read_text(encoding="utf-8", errors="replace")

    tables = extract_tables(text_content)
    result.update(
        {
            "text_content": text_content,
            "tables": tables,
        }
    )
    print(f"    text length: {len(text_content)}")
    print(f"    markdown tables: {len(tables)}")
    return result


def extract_markdown_tables(text: str) -> List[str]:
    """Return Markdown pipe-table blocks from parsed text."""

    tables: List[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|") and line.strip().endswith("|"):
            block = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                block.append(lines[i])
                i += 1
            if len(block) >= 2 and re.search(r"\|[\s:\-]+\|", block[1]):
                tables.append("\n".join(block))
            continue
        i += 1
    return tables


class _HtmlTableParser(HTMLParser):
    """Convert HTML tables emitted by MinerU into Markdown pipe tables."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self._table: List[List[str]] | None = None
        self._row: List[str] | None = None
        self._cell: List[str] | None = None

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def extract_html_tables(text: str) -> List[str]:
    """Return MinerU HTML tables as Markdown pipe-table blocks."""

    parser = _HtmlTableParser()
    parser.feed(text)
    tables: List[str] = []
    for rows in parser.tables:
        width = len(rows[0])
        if width < 2 or any(len(row) != width for row in rows):
            continue
        escaped = [[cell.replace("|", r"\|") for cell in row] for row in rows]
        lines = [
            "| " + " | ".join(escaped[0]) + " |",
            "| " + " | ".join(["---"] * width) + " |",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in escaped[1:])
        tables.append("\n".join(lines))
    return tables


def extract_tables(text: str) -> List[str]:
    """Return all supported table representations from MinerU Markdown."""

    return extract_markdown_tables(text) + extract_html_tables(text)


def parse_reaction_table(table_text: str, entry_num: int = 0) -> List[Dict[str, Any]]:
    """Parse a Markdown reaction-condition table into structured rows."""

    reactions: List[Dict[str, Any]] = []
    lines = [line for line in table_text.strip().splitlines() if line.strip()]
    if len(lines) < 3:
        return reactions

    headers = [h.strip() for h in lines[0].split("|") if h.strip()]
    for row_idx, line in enumerate(lines[2:], start=1):
        values = [v.strip() for v in line.split("|") if v.strip()]
        if len(values) != len(headers):
            continue

        reaction: Dict[str, Any] = {
            "reaction_id": f"RXN_T{entry_num:02d}_{row_idx:03d}",
        }
        for header, value in zip(headers, values):
            key = normalize_header(header)
            if key == "yield_raw":
                match = re.search(r"(\d+(?:\.\d+)?)", value)
                if match:
                    reaction["yield_value"] = float(match.group(1))
                reaction["yield_raw"] = value
            elif key:
                reaction[key] = value
            else:
                reaction[header] = value

        reactions.append(reaction)
    return reactions


def normalize_header(header: str) -> str | None:
    text = header.lower()
    if "entry" in text or text in {"no", "no."}:
        return "entry"
    if "yield" in text:
        return "yield_raw"
    if "ee" in text or "enantio" in text:
        return "ee_value"
    if "catalyst" in text or re.search(r"\bcat\b", text):
        return "catalyst"
    if "ligand" in text:
        return "ligand"
    if "solvent" in text or "solv" in text:
        return "solvent"
    if "temp" in text:
        return "temperature"
    if re.search(r"^\s*t\s*(?:\(|\[)", text):
        return "temperature"
    if "time" in text:
        return "time"
    if "oxidant" in text or "additive" in text:
        return "oxidant"
    if "base" in text:
        return "base"
    if "product" in text:
        return "product"
    if "substrate" in text or "reactant" in text:
        return "reactant"
    return None


def extract_reactions_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract likely reaction conditions from free text paragraphs."""

    patterns = {
        "temperature": r"(\b\d+\s*(?:deg\s*C|degrees?\s*C|C)\b|\brt\b|\breflux\b|room temperature|ambient)",
        "time": r"(\b\d+(?:\.\d+)?\s*(?:h|hr|hrs|hour|hours|min|minute|minutes)\b)",
        "yield_raw": r"((?:yield|afforded|obtained)[^.]{0,80}?\b\d+(?:\.\d+)?\s*%)",
        "catalyst": r"\b((?:Pd|Ni|Cu|Rh|Ru|Ir|Fe|Co|Mn|Ag|Au|Pt)\s*(?:\([^)]*\))?)",
        "ligand": r"\b(L\d+|PPh3|dppf|BINAP|XPhos|SPhos|JohnPhos|BrettPhos)\b",
        "oxidant": r"\b(DTBQ|DMBQ|TBHP|BQ|DDQ|Selectfluor|NFSI)\b",
        "solvent": r"\b(MeOH|EtOH|DMF|DMSO|THF|toluene|acetone|DCM|CH2Cl2|CH3CN|MeCN|dioxane)\b",
        "base": r"\b(K2CO3|Cs2CO3|Na2CO3|K3PO4|NaOH|KOH|Et3N|DIPEA|DBU)\b",
    }

    reactions: List[Dict[str, Any]] = []
    paragraphs = re.split(r"\n\s*\n", text)
    for idx, paragraph in enumerate(paragraphs):
        clean = " ".join(paragraph.split())
        if len(clean) < 80:
            continue
        if not any(word in clean.lower() for word in ["reaction", "yield", "catalyst", "condition", "optimized"]):
            continue

        reaction: Dict[str, Any] = {
            "reaction_id": f"RXN_TEXT_{idx:03d}",
            "source": "text",
            "confidence": 0.5,
            "raw_text": clean[:500],
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, clean, re.IGNORECASE)
            if match:
                reaction[key] = match.group(1)

        extracted = [key for key in patterns if key in reaction]
        if len(extracted) >= 2:
            reactions.append(reaction)
    return reactions


def save_reactions(reactions: List[Dict[str, Any]], output_dir: Path, output_format: str = "csv") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_format == "json":
        json_file = output_dir / "reaction_data.json"
        json_file.write_text(
            json.dumps(
                {
                    "extraction_date": datetime.now().isoformat(),
                    "total_reactions": len(reactions),
                    "reactions": reactions,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"  JSON saved: {json_file}")
        return

    csv_file = output_dir / "reaction_data.csv"
    if not reactions:
        csv_file.write_text("", encoding="utf-8")
        print("  No reaction data found.")
        return

    fieldnames = sorted({field for reaction in reactions for field in reaction.keys()})
    with csv_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for reaction in reactions:
            writer.writerow(
                {
                    key: "; ".join(map(str, value)) if isinstance(value, list) else value
                    for key, value in reaction.items()
                }
            )
    print(f"  CSV saved: {csv_file}")


def process_single_pdf(input_pdf: str, output_dir: str, args: argparse.Namespace) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    mode = "tables" if args.tables_only else "text" if args.text_only else "all"
    print(f"Output: {output_path}")
    print(f"Mode: {mode}")
    print(f"Format: {args.output_format}")

    mineru_result = run_mineru(
        input_pdf,
        output_dir,
        method=args.method,
        lang=args.lang,
        device=args.device,
        page_range=args.page_range,
    )
    if not mineru_result.get("success"):
        print(f"  PDF parsing failed: {mineru_result.get('error')}")
        return

    text_content = mineru_result.get("text_content", "")
    tables = mineru_result.get("tables", [])
    all_reactions: List[Dict[str, Any]] = []

    if not args.text_only and tables:
        print("  [2/3] Extracting reactions from tables...")
        for table_idx, table in enumerate(tables):
            table_reactions = parse_reaction_table(table, table_idx)
            for reaction in table_reactions:
                reaction["source"] = f"table_{table_idx}"
                reaction["confidence"] = 0.9
            all_reactions.extend(table_reactions)
        print(f"    table reactions: {len([r for r in all_reactions if r.get('source', '').startswith('table_')])}")

    if not args.tables_only and text_content:
        print("  [3/3] Extracting reactions from text...")
        text_reactions = extract_reactions_from_text(text_content)
        all_reactions.extend(text_reactions)
        print(f"    text reactions: {len(text_reactions)}")

    print(f"Done: {Path(input_pdf).name}")
    print(f"  reactions: {len(all_reactions)}")
    save_reactions(all_reactions, output_path, args.output_format)

    log_file = output_path / "extraction_log.txt"
    log_file.write_text(
        "\n".join(
            [
                "Extraction Log",
                "=" * 60,
                f"Source: {input_pdf}",
                f"Date: {datetime.now().isoformat()}",
                f"MinerU mode: {mineru_result.get('mode')}",
                f"Markdown: {mineru_result.get('markdown_file')}",
                f"Total reactions: {len(all_reactions)}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"  Log saved: {log_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract chemistry reaction data from PDF literature.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s -i paper.pdf -o ./output\n"
            "  %(prog)s -i paper.pdf -o ./output --tables-only\n"
            "  %(prog)s -i ./papers/ -o ./output --batch\n"
        ),
    )
    parser.add_argument("-i", "--input", required=True, help="Input PDF file or directory")
    parser.add_argument(
        "-o",
        "--output",
        default="~/.openclaw/media/reaction-data-extraction",
        help="Output directory",
    )
    parser.add_argument("--tables-only", action="store_true", help="Extract table rows only")
    parser.add_argument("--text-only", action="store_true", help="Extract free-text reactions only")
    parser.add_argument("--output-format", default="csv", choices=["csv", "json"], help="Output format")
    parser.add_argument(
        "--method",
        default="auto",
        choices=["auto", "txt", "ocr"],
        help="Parsing mode. In API mode, only ocr toggles MinerU OCR.",
    )
    parser.add_argument("--lang", default="en", help="Document language")
    parser.add_argument("--page-range", default=None, help="Optional page range, for example 1-10")
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda"],
        help="Kept for compatibility; ignored in API mode.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--batch", action="store_true", help="Batch process a directory")

    args = parser.parse_args()
    output_base = Path(os.path.expanduser(args.output))
    input_path = Path(os.path.expanduser(args.input))

    if input_path.is_dir():
        pdf_files = sorted(input_path.glob("*.pdf"))
        print(f"Batch mode: {len(pdf_files)} PDF files")
        for pdf_file in pdf_files:
            print(f"\nProcessing: {pdf_file.name}")
            process_single_pdf(str(pdf_file), str(output_base / pdf_file.stem), args)
    elif input_path.is_file():
        process_single_pdf(str(input_path), str(output_base / input_path.stem), args)
    else:
        print(f"Input path does not exist: {input_path}")
        sys.exit(1)

    print("=" * 60)
    print(f"All done. Output: {output_base}")


if __name__ == "__main__":
    main()
