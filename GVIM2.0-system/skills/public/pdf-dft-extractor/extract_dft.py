#!/usr/bin/env python3
"""Extract DFT coordinates from PDF files and generate Gaussian .gjf files."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _load_shared_client() -> None:
    for parent in Path(__file__).resolve().parents:
        shared_dir = parent / "_gvim_shared"
        if shared_dir.exists():
            sys.path.insert(0, str(shared_dir))
            return


_load_shared_client()
from mineru_api import parse_pdf_with_mineru_api  # noqa: E402


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
ELEMENT = (
    r"H|He|Li|Be|B|C|N|O|F|Ne|Na|Mg|Al|Si|P|S|Cl|Ar|K|Ca|Sc|Ti|V|Cr|Mn|"
    r"Fe|Co|Ni|Cu|Zn|Ga|Ge|As|Se|Br|Kr|Rb|Sr|Y|Zr|Nb|Mo|Tc|Ru|Rh|Pd|Ag|"
    r"Cd|In|Sn|Sb|Te|I|Xe|Cs|Ba|La|Ce|Pr|Nd|Pm|Sm|Eu|Gd|Tb|Dy|Ho|Er|Tm|"
    r"Yb|Lu|Hf|Ta|W|Re|Os|Ir|Pt|Au|Hg|Tl|Pb|Bi"
)
LOG_PATTERN = re.compile(
    r"([A-Za-z0-9][\w\-]*(?:_b3pw91|_pbe0|_wb97xd|_b3lyp|_m06|_m062x))\.log",
    re.IGNORECASE,
)


def extract_molecules_from_markdown(md_content: str) -> List[Tuple[str, str]]:
    """Extract molecule names and Cartesian coordinates from Markdown text."""

    section = md_content
    for marker in ("Computed coordinates", "Cartesian coordinates", "XYZ coordinates", "Coordinates"):
        if marker in md_content:
            section = md_content.split(marker, 1)[1]
            break

    molecules: List[Tuple[str, str]] = []
    log_matches = list(LOG_PATTERN.finditer(section))
    for idx, match in enumerate(log_matches):
        mol_name = sanitize_filename(match.group(1))
        start = match.end()
        end = log_matches[idx + 1].start() if idx + 1 < len(log_matches) else len(section)
        coords = extract_coordinate_lines(section[start:end])
        if coords and len(coords) < 10000:
            molecules.append((mol_name, "\n".join(coords)))
    return molecules


def extract_coordinate_lines(section: str) -> List[str]:
    """Extract and normalize coordinate lines from HTML table or plain text."""

    coords: List[str] = []
    html_pattern = re.compile(
        rf"<tr>\s*<td>\s*({ELEMENT})\s*</td>\s*"
        rf"<td>\s*({NUMBER})\s*</td>\s*"
        rf"<td>\s*({NUMBER})\s*</td>\s*"
        rf"<td>\s*({NUMBER})\s*</td>\s*</tr>",
        re.IGNORECASE,
    )
    for element, x, y, z in html_pattern.findall(section):
        coords.append(format_coordinate(element, x, y, z))

    if coords:
        return coords

    text_pattern = re.compile(
        rf"^\s*({ELEMENT})[\s,]+({NUMBER})[\s,]+({NUMBER})[\s,]+({NUMBER})(?:\s|,|$)",
        re.IGNORECASE | re.MULTILINE,
    )
    for element, x, y, z in text_pattern.findall(section):
        coords.append(format_coordinate(element, x, y, z))
    return coords


def format_coordinate(element: str, x: str, y: str, z: str) -> str:
    element = element.strip()
    element = element[0].upper() + element[1:].lower() if len(element) > 1 else element.upper()
    return f"{element:>2}  {float(x):16.8f}{float(y):16.8f}{float(z):16.8f}"


def sanitize_filename(name: str) -> str:
    safe = re.sub(r'[<>":/\\|?*\x00-\x1f]', "_", name)
    safe = re.sub(r"\s+", "_", safe).strip("._")
    return safe[:100] or "molecule"


def write_gjf(
    output_path: str,
    molecule_name: str,
    coords_text: str,
    charge: int = 0,
    multiplicity: int = 1,
    cpu: int = 64,
    mem: str = "128GB",
    method: str = "B3PW91/def2TZVP em=d3bj",
    solvent: str = "SMD(toluene)",
    keywords: str = "opt freq",
) -> str:
    """Write one Gaussian input file."""

    safe_name = sanitize_filename(molecule_name)
    content = (
        f"%chk={safe_name}.chk\n"
        f"%mem={mem}\n"
        f"%nprocshared={cpu}\n"
        f"# {method} nosymm int=ultrafine {solvent} {keywords}\n\n"
        f"{molecule_name}\n\n"
        f"{charge} {multiplicity}\n"
        f"{coords_text}\n\n"
    )
    Path(output_path).write_text(content, encoding="utf-8")
    return output_path


def generate_readme(
    output_dir: str,
    pdf_name: str,
    molecules: List[Tuple[str, str]],
    cpu: int,
    mem: str,
    method: str,
) -> str:
    """Generate a simple output README."""

    readme_path = Path(output_dir) / "README.txt"
    lines = [
        "DFT coordinate extraction",
        "=" * 50,
        "",
        f"Source PDF: {pdf_name}",
        f"Method: {method}",
        f"CPU cores: {cpu}",
        f"Memory: {mem}",
        f"Molecule count: {len(molecules)}",
        "",
        "Generated files:",
    ]
    lines.extend(f"  - {mol_name}.gjf" for mol_name, _ in molecules)
    readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(readme_path)


def process_pdf(
    pdf_path: str,
    output_dir: Optional[str] = None,
    cpu: int = 64,
    mem: str = "128GB",
    method: str = "B3PW91/def2TZVP em=d3bj",
    solvent: str = "SMD(toluene)",
    charge: int = 0,
    multiplicity: int = 1,
    keywords: str = "opt freq",
    keep_temp: bool = False,
) -> Dict:
    """Process one PDF file and generate Gaussian input files."""

    source_pdf = Path(pdf_path).expanduser().resolve()
    if not source_pdf.exists():
        return {"success": False, "error": f"Input file does not exist: {source_pdf}"}

    output_path = Path(output_dir or source_pdf.stem).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\nProcessing: {source_pdf.name}")
    print(f"Output: {output_path}")

    temp_output = output_path / "temp_mineru_api"
    try:
        print("  Converting PDF to Markdown with MinerU API...")
        mineru_result = parse_pdf_with_mineru_api(
            source_pdf,
            temp_output,
            language="en",
            enable_table=True,
            enable_formula=True,
        )
        if not mineru_result.get("success"):
            return {"success": False, "error": mineru_result.get("error")}

        md_file = Path(mineru_result["markdown_file"])
        md_content = md_file.read_text(encoding="utf-8", errors="replace")

        print("  Extracting DFT coordinates...")
        molecules = extract_molecules_from_markdown(md_content)
        if not molecules:
            if not keep_temp:
                shutil.rmtree(temp_output, ignore_errors=True)
            return {"success": False, "error": "No DFT coordinate blocks were found."}

        print(f"  Found {len(molecules)} molecules.")
        generated_files: List[str] = []
        for mol_name, coords in molecules:
            gjf_path = output_path / f"{mol_name}.gjf"
            try:
                write_gjf(
                    str(gjf_path),
                    mol_name,
                    coords,
                    charge=charge,
                    multiplicity=multiplicity,
                    cpu=cpu,
                    mem=mem,
                    method=method,
                    solvent=solvent,
                    keywords=keywords,
                )
                generated_files.append(gjf_path.name)
            except Exception as exc:
                print(f"    warning: failed to generate {mol_name}: {exc}")

        readme_path = generate_readme(str(output_path), source_pdf.name, molecules, cpu, mem, method)

        if not keep_temp:
            shutil.rmtree(temp_output, ignore_errors=True)

        return {
            "success": True,
            "pdf": source_pdf.name,
            "output_dir": str(output_path),
            "molecule_count": len(molecules),
            "generated_files": generated_files,
            "readme": readme_path,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def batch_process(pdf_dir: str, output_base_dir: str = "./dft_output", **kwargs) -> List[Dict]:
    """Process every PDF in a directory."""

    source_dir = Path(pdf_dir).expanduser().resolve()
    output_base = Path(output_base_dir).expanduser().resolve()
    output_base.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(source_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {source_dir}")
        return []

    print(f"Found {len(pdf_files)} PDF files")
    print("=" * 60)

    results: List[Dict] = []
    for pdf_file in pdf_files:
        result = process_pdf(
            str(pdf_file),
            output_dir=str(output_base / pdf_file.stem),
            **kwargs,
        )
        results.append(result)
        if result.get("success"):
            print(f"Success: {result['molecule_count']} molecules")
        else:
            print(f"Failed: {result.get('error', 'unknown error')}")

    print("=" * 60)
    print(f"Total: {len(pdf_files)}")
    print(f"Success: {sum(1 for item in results if item.get('success'))}")
    print(f"Failed: {sum(1 for item in results if not item.get('success'))}")
    print(f"Output: {output_base}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract DFT coordinates from PDFs and generate Gaussian .gjf files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s paper.pdf\n"
            "  %(prog)s ./pdfs/ -o ./output/\n"
            "  %(prog)s paper.pdf --cpu 64 --mem 128GB --method \"B3LYP/6-31G(d)\"\n"
        ),
    )
    parser.add_argument("input", help="PDF file or directory containing PDFs")
    parser.add_argument("-o", "--output", default="./dft_output", help="Output directory")
    parser.add_argument("--cpu", type=int, default=64, help="CPU cores for Gaussian input")
    parser.add_argument("--mem", default="128GB", help="Memory for Gaussian input")
    parser.add_argument("--method", default="B3PW91/def2TZVP em=d3bj", help="Gaussian method")
    parser.add_argument("--solvent", default="SMD(toluene)", help="Solvent model")
    parser.add_argument("--charge", type=int, default=0, help="Molecular charge")
    parser.add_argument("--multiplicity", type=int, default=1, help="Spin multiplicity")
    parser.add_argument("--keywords", default="opt freq", help="Gaussian keywords")
    parser.add_argument("--keep-temp", action="store_true", help="Keep MinerU Markdown output")

    args = parser.parse_args()
    input_path = Path(args.input).expanduser()
    process_kwargs = {
        "cpu": args.cpu,
        "mem": args.mem,
        "method": args.method,
        "solvent": args.solvent,
        "charge": args.charge,
        "multiplicity": args.multiplicity,
        "keywords": args.keywords,
        "keep_temp": args.keep_temp,
    }

    if input_path.is_dir():
        batch_process(str(input_path), output_base_dir=args.output, **process_kwargs)
        return

    result = process_pdf(str(input_path), output_dir=args.output, **process_kwargs)
    if result.get("success"):
        print("\nProcessing succeeded.")
        print(f"  PDF: {result['pdf']}")
        print(f"  Output: {result['output_dir']}")
        print(f"  Molecules: {result['molecule_count']}")
        print(f"  Files: {result['generated_files']}")
    else:
        print(f"\nProcessing failed: {result.get('error', 'unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
