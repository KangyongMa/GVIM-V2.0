from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(r"E:\Demo of GVIM\deer-flow-mainnew")
SI = ROOT / "Supporting_Information"
SUBMISSION_SI = ROOT / "Chemical_Science_Submission" / "Supporting_Information"
RESULTS = ROOT / "research-demos" / "results"

TASK_ARTIFACTS = {
    "esol_scaffold_aware.json": RESULTS / "fast_ml_showcase" / "frontend_esol_scaffold_aware.json",
    "matbench_steels_frontend_fold0.json": RESULTS / "fast_ml_showcase" / "frontend_steels_single_run_recheck.json",
    "matbench_steels_official_5fold.json": RESULTS / "matbench_steels_5fold" / "independent_evaluation.json",
    "mineru_reaction_table.json": RESULTS / "mineru_reaction_table" / "frontend_9dc67557_evaluation.json",
    "msms_candidate_retrieval.json": RESULTS / "msms_retrieval" / "frontend_abe44a97_evaluation.json",
    "chemu_entity_extraction.json": RESULTS / "chemu" / "frontend_dbb54347_evaluation.json",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def copy_task_artifacts() -> None:
    target = SI / "artifacts" / "task_native"
    target.mkdir(parents=True, exist_ok=True)
    for name, source in TASK_ARTIFACTS.items():
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, target / name)


def copy_reproducibility_scripts() -> None:
    target = SI / "code"
    target.mkdir(parents=True, exist_ok=True)
    script_dir = ROOT / "manuscript_assets" / "scripts"
    for name in (
        "build_supporting_information.py",
        "prepare_supporting_information_package.py",
        "draw_bace_temporal_publication_figure.py",
        "redraw_publication_figures.py",
        "redraw_true_main_case_figure.py",
    ):
        shutil.copy2(script_dir / name, target / name)


def frontmatter_value(text: str, key: str) -> str:
    if not text.startswith("---"):
        return ""
    block = text.split("---", 2)[1]
    for line in block.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return ""


def write_skills_inventory() -> None:
    skills_root = ROOT / "deer-flow-main" / "skills"
    config = json.loads((ROOT / "deer-flow-main" / "extensions_config.json").read_text(encoding="utf-8"))
    configured = config.get("skills", {})
    output = SI / "source_data" / "skills_inventory.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(skills_root.rglob("SKILL.md")):
        content = path.read_text(encoding="utf-8")
        name = frontmatter_value(content, "name") or path.parent.name
        relative = path.relative_to(ROOT / "deer-flow-main").as_posix()
        category = relative.split("/")[1] if "/" in relative else ""
        state = configured.get(name, {}).get("enabled")
        rows.append(
            [
                name,
                category,
                relative,
                "true" if state is True else "false" if state is False else "not_explicitly_set",
                frontmatter_value(content, "license"),
                digest(path),
            ]
        )
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", "category", "skill_file", "extensions_config_state", "declared_license", "skill_file_sha256"])
        writer.writerows(rows)
    if len(rows) != 147:
        raise ValueError(f"Expected 147 discoverable SKILL.md files, found {len(rows)}")


def pick(mapping: dict, *candidates: tuple[str, ...]):
    for candidate in candidates:
        value = mapping
        try:
            for key in candidate:
                value = value[key]
            return value
        except (KeyError, TypeError):
            continue
    raise KeyError(candidates)


def verify_selected_values() -> dict:
    task = SI / "artifacts" / "task_native"
    esol = json.loads((task / "esol_scaffold_aware.json").read_text(encoding="utf-8"))
    steels = json.loads((task / "matbench_steels_frontend_fold0.json").read_text(encoding="utf-8"))
    mineru = json.loads((task / "mineru_reaction_table.json").read_text(encoding="utf-8"))
    msms = json.loads((task / "msms_candidate_retrieval.json").read_text(encoding="utf-8"))
    chemu = json.loads((task / "chemu_entity_extraction.json").read_text(encoding="utf-8"))
    temporal = json.loads((SI / "artifacts" / "bace_temporal" / "metrics.json").read_text(encoding="utf-8"))

    values = {
        "esol_mae": float(pick(esol, ("metrics", "mae"))),
        "steels_fold0_mae": float(pick(steels, ("aggregate_metrics", "mae", "mean"))),
        "mineru_exact_f1": float(pick(mineru, ("exact_match_f1",))),
        "msms_top1": float(pick(msms, ("top1_accuracy",))),
        "chemu_exact_f1": float(pick(chemu, ("exact_match", "f1"), ("metrics", "exact_f1"), ("exact_f1",))),
        "bace_temporal_mae": float(temporal["regression_metrics"][0]["MAE"]),
    }
    expected = {
        "esol_mae": 0.603,
        "steels_fold0_mae": 111.444,
        "mineru_exact_f1": 0.981,
        "msms_top1": 0.800,
        "chemu_exact_f1": 0.817,
        "bace_temporal_mae": 0.8215,
    }
    checks = {key: abs(values[key] - target) < 5e-4 for key, target in expected.items()}
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"Supporting Information verification failed: {failed}; values={values}")
    return {
        "status": "passed",
        "checks": checks,
        "observed_values": values,
        "source": "archived GVIM result artifacts",
    }


def role_for(relative: str) -> str:
    if relative.endswith("GVIM2.0_Supporting_Information.docx"):
        return "Supporting Information manuscript"
    if relative.startswith("artifacts/"):
        return "Archived workflow output"
    if relative.startswith("source_data/"):
        return "Figure or benchmark source data"
    if relative.startswith("figures/"):
        return "Publication figure"
    if relative.startswith("prompts/"):
        return "Front-end task prompt or manifest"
    if relative.startswith("code/"):
        return "Reproducibility code"
    return "Package documentation"


def write_manifest() -> None:
    manifest = SI / "MANIFEST.csv"
    files = [p for p in SI.rglob("*") if p.is_file() and p.name != manifest.name]
    with manifest.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["relative_path", "bytes", "sha256", "role"])
        for path in sorted(files, key=lambda p: p.as_posix().lower()):
            relative = path.relative_to(SI).as_posix()
            writer.writerow([relative, path.stat().st_size, digest(path), role_for(relative)])


def write_readme() -> None:
    text = """GVIM 2.0 Supporting Information package

Primary document
  GVIM2.0_Supporting_Information.docx

Package organization
  artifacts/    Archived machine-readable outputs from the reported workflows.
  source_data/  Source tables used for benchmark and figure reconstruction.
  figures/      High-resolution PNG/TIFF and vector PDF/SVG figure files.
  prompts/      The blinded temporal-validation prompts and task manifests.
  code/         Scripts used to build the SI and regenerate reported figures.
  MANIFEST.csv  File sizes, SHA-256 identifiers and artifact roles.
  verification_report.json  Automated checks of selected headline values.

Evidence boundary
  All numerical claims are linked to archived files or public benchmark source
  data. Discovery studies are retrospective. The package contains no wet-lab
  validation and does not claim prospective compound or material discovery.

Important distinction
  The Matbench steels fold-0 result is the front-end demonstration. The official
  five-fold Matbench result is a separate local independent evaluation and is
  labelled as such in both the manuscript and Supporting Information.
"""
    (SI / "README.txt").write_text(text, encoding="utf-8")


def mirror_submission_folder() -> None:
    if SUBMISSION_SI.exists():
        shutil.rmtree(SUBMISSION_SI)
    shutil.copytree(SI, SUBMISSION_SI)


def main() -> None:
    SI.mkdir(parents=True, exist_ok=True)
    copy_task_artifacts()
    copy_reproducibility_scripts()
    write_skills_inventory()
    report = verify_selected_values()
    (SI / "verification_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_readme()
    write_manifest()
    mirror_submission_folder()
    print(SI)
    print(SUBMISSION_SI)


if __name__ == "__main__":
    main()
