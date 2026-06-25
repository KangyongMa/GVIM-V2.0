"""Package-backed crystal-structure analysis and XRD simulation."""

from __future__ import annotations

import json
from collections import Counter
from io import StringIO
from typing import Any

from .errors import MaterialsDependencyError


def _require_pymatgen():
    try:
        import spglib  # noqa: F401
        from pymatgen.analysis.diffraction.xrd import XRDCalculator
        from pymatgen.core import Structure
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    except Exception as exc:  # pragma: no cover - depends on deployment env
        raise MaterialsDependencyError(
            "pymatgen and spglib are required for crystal structure analysis and XRD simulation"
        ) from exc
    return Structure, SpacegroupAnalyzer, XRDCalculator


def _require_ase():
    try:
        from ase.io import read
    except Exception as exc:  # pragma: no cover - depends on deployment env
        raise MaterialsDependencyError("ase is required for XYZ structure parsing") from exc
    return read


def _require_local_env():
    try:
        try:
            from pymatgen.core.local_env import CrystalNN, MinimumDistanceNN
        except ImportError:
            from pymatgen.analysis.local_env import CrystalNN, MinimumDistanceNN
    except Exception as exc:  # pragma: no cover - depends on deployment env
        raise MaterialsDependencyError(
            "pymatgen local_env is required for local coordination analysis"
        ) from exc
    return CrystalNN, MinimumDistanceNN


def _require_structure_matcher():
    try:
        try:
            from pymatgen.core.structure_matcher import StructureMatcher
        except ImportError:
            from pymatgen.analysis.structure_matcher import StructureMatcher
    except Exception as exc:  # pragma: no cover - depends on deployment env
        raise MaterialsDependencyError(
            "pymatgen StructureMatcher is required for structure matching"
        ) from exc
    return StructureMatcher


def _gemmi_cif_summary(text: str) -> dict[str, Any]:
    try:
        import gemmi
    except Exception:
        return {"available": False, "source": "gemmi_not_installed"}
    try:
        document = gemmi.cif.read_string(text)
        blocks = [block.name for block in document]
        return {
            "available": True,
            "source": "gemmi.cif.read_string",
            "block_count": len(blocks),
            "blocks": blocks[:10],
            "truncated": len(blocks) > 10,
        }
    except Exception as exc:
        return {
            "available": True,
            "source": "gemmi.cif.read_string",
            "error": str(exc),
        }


def _guess_structure_format(text: str, file_format: str | None) -> str:
    fmt = (file_format or "auto").strip().lower()
    if fmt not in {"", "auto"}:
        aliases = {
            "vasp": "poscar",
            "contcar": "poscar",
            "cif": "cif",
            "poscar": "poscar",
            "xyz": "xyz",
        }
        if fmt not in aliases:
            raise ValueError("file_format must be cif, poscar, xyz, or auto")
        return aliases[fmt]

    sample = text[:1000].lower()
    if "data_" in sample or "_cell_length_a" in sample or "_atom_site" in sample:
        return "cif"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 8:
        try:
            float(lines[1].split()[0])
            return "poscar"
        except (IndexError, ValueError):
            pass
    if lines and lines[0].isdigit():
        return "xyz"
    raise ValueError("could not infer structure format; provide file_format")


def _coerce_structure_text(structure_text: Any) -> str:
    text = str(structure_text or "").strip()
    if not text:
        raise ValueError("structure_text is required")
    if len(text) > 2_000_000:
        raise ValueError("structure_text is limited to 2 MB")
    return text


def _format_hkl_label(hkl_items: list[dict[str, Any]], max_terms: int = 1) -> str:
    labels: list[str] = []
    for item in hkl_items[:max(1, max_terms)]:
        hkl = item.get("hkl")
        if not isinstance(hkl, list) or not hkl:
            continue
        labels.append("(" + "".join(str(int(value)) for value in hkl) + ")")
    if not labels:
        return ""
    remaining = len(hkl_items) - len(labels)
    suffix = f"+{remaining}" if remaining > 0 else ""
    return ",".join(labels) + suffix


def _select_xrd_annotation_indices(
    peaks: list[dict[str, Any]],
    *,
    max_annotations: int = 12,
    min_relative_intensity: float = 8.0,
) -> list[int]:
    if not peaks or max_annotations <= 0:
        return []

    min_intensity = max(0.0, float(min_relative_intensity))
    peak_count = len(peaks)
    first_angle = float(peaks[0].get("two_theta", 0.0))
    last_angle = float(peaks[-1].get("two_theta", first_angle))
    span = max(1.0, last_angle - first_angle)
    min_separation = max(1.5, span / 42.0)
    hard_limit = min(max_annotations, peak_count)
    required_floor = min(5, hard_limit)

    ranked = sorted(
        range(peak_count),
        key=lambda index: float(peaks[index].get("intensity", 0.0)),
        reverse=True,
    )
    selected: list[int] = []

    def has_room(candidate_index: int, separation: float) -> bool:
        candidate_angle = float(peaks[candidate_index].get("two_theta", 0.0))
        return all(
            abs(candidate_angle - float(peaks[selected_index].get("two_theta", 0.0))) >= separation
            for selected_index in selected
        )

    for index in ranked:
        intensity = float(peaks[index].get("intensity", 0.0))
        if intensity < min_intensity and len(selected) >= required_floor:
            continue
        if has_room(index, min_separation):
            selected.append(index)
        if len(selected) >= hard_limit:
            break

    if len(selected) < required_floor:
        relaxed_separation = min_separation / 2
        for index in ranked:
            if index in selected:
                continue
            if has_room(index, relaxed_separation):
                selected.append(index)
            if len(selected) >= required_floor:
                break

    return sorted(selected)


def _composition_from_counter(counter: Counter[str]) -> dict[str, float]:
    return {element: float(amount) for element, amount in sorted(counter.items())}


def _analyze_xyz(text: str) -> dict[str, Any]:
    read = _require_ase()
    atoms = read(StringIO(text), format="xyz")
    symbols = list(atoms.get_chemical_symbols())
    composition = _composition_from_counter(Counter(symbols))
    positions = atoms.get_positions()
    bounds = {
        "x": [round(float(positions[:, 0].min()), 6), round(float(positions[:, 0].max()), 6)],
        "y": [round(float(positions[:, 1].min()), 6), round(float(positions[:, 1].max()), 6)],
        "z": [round(float(positions[:, 2].min()), 6), round(float(positions[:, 2].max()), 6)],
    }
    return {
        "success": True,
        "version": "2.0",
        "source": "ase.io.read",
        "engine": "ase",
        "format": "xyz",
        "periodic": False,
        "formula": "".join(
            f"{element}{int(amount) if amount != 1 else ''}"
            for element, amount in composition.items()
        ),
        "composition": composition,
        "site_count": len(symbols),
        "coordinate_bounds_angstrom": bounds,
        "available_operations": ["formula_summary"],
        "data_quality": {
            "computed_from": "uploaded_xyz",
            "experimental": False,
        },
        "limitations": [
            "XYZ does not contain periodic lattice information, so space group and theoretical powder XRD are unavailable.",
        ],
    }


def _load_periodic_structure(text: str, fmt: str):
    Structure, _, _ = _require_pymatgen()
    if fmt not in {"cif", "poscar"}:
        raise ValueError("periodic structure analysis requires CIF or POSCAR text")
    return Structure.from_str(text, fmt=fmt)


def _round_float(value: Any, digits: int = 6) -> float | None:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _json_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _neighbor_distance(structure, center_index: int, neighbor_info: dict[str, Any]) -> float | None:
    site_index = neighbor_info.get("site_index")
    image = neighbor_info.get("image")
    try:
        if isinstance(site_index, int):
            return _round_float(structure.get_distance(center_index, site_index, jimage=image), 6)
    except Exception:
        pass
    try:
        return _round_float(structure[center_index].distance(neighbor_info["site"]), 6)
    except Exception:
        return None


def analyze_structure(
    structure_text: Any,
    file_format: str | None = "auto",
    symprec: float = 0.1,
) -> dict[str, Any]:
    """Analyze a CIF/POSCAR/XYZ payload with mature scientific packages."""
    text = _coerce_structure_text(structure_text)
    fmt = _guess_structure_format(text, file_format)
    if fmt == "xyz":
        return _analyze_xyz(text)

    _, SpacegroupAnalyzer, _ = _require_pymatgen()
    structure = _load_periodic_structure(text, fmt)
    lattice = structure.lattice

    try:
        analyzer = SpacegroupAnalyzer(structure, symprec=float(symprec or 0.1))
        sg_payload: dict[str, Any] = {
            "symbol": analyzer.get_space_group_symbol(),
            "number": analyzer.get_space_group_number(),
            "crystal_system": analyzer.get_crystal_system(),
            "hall": analyzer.get_hall(),
            "symprec": float(symprec or 0.1),
            "engine": "spglib_via_pymatgen",
        }
    except Exception as exc:
        sg_payload = {
            "error": str(exc),
            "symprec": float(symprec or 0.1),
            "engine": "spglib_via_pymatgen",
        }

    species = Counter(str(site.specie) for site in structure.sites)
    return {
        "success": True,
        "version": "2.0",
        "source": "pymatgen.core.Structure",
        "engine": "pymatgen",
        "format": fmt,
        "periodic": True,
        "formula": structure.composition.formula,
        "reduced_formula": structure.composition.reduced_formula,
        "composition": {
            element.symbol: float(amount)
            for element, amount in structure.composition.items()
        },
        "site_count": len(structure),
        "species_counts": dict(sorted(species.items())),
        "density_g_cm3": round(float(structure.density), 6),
        "lattice": {
            "a": round(float(lattice.a), 6),
            "b": round(float(lattice.b), 6),
            "c": round(float(lattice.c), 6),
            "alpha": round(float(lattice.alpha), 6),
            "beta": round(float(lattice.beta), 6),
            "gamma": round(float(lattice.gamma), 6),
            "volume": round(float(lattice.volume), 6),
        },
        "space_group": sg_payload,
        "available_operations": [
            "formula_summary",
            "space_group_detection",
            "theoretical_xrd_simulation",
        ],
        "data_quality": {
            "computed_from": f"uploaded_{fmt}",
            "experimental": False,
        },
        "limitations": [
            "Structure parsing does not prove phase purity or thermodynamic stability.",
            "Space-group assignment depends on the supplied coordinates and symprec.",
        ],
    }


def analyze_local_environment(
    structure_text: Any,
    file_format: str | None = "auto",
    method: str = "crystal_nn",
    symprec: float = 0.1,
    max_sites: int = 128,
    max_neighbors_per_site: int = 16,
) -> dict[str, Any]:
    """Analyze site coordination environments for a periodic structure."""

    text = _coerce_structure_text(structure_text)
    fmt = _guess_structure_format(text, file_format)
    if fmt == "xyz":
        raise ValueError("local environment analysis requires a periodic CIF or POSCAR structure")

    structure = _load_periodic_structure(text, fmt)
    site_limit = max(1, min(int(max_sites or 128), 256))
    neighbor_limit = max(1, min(int(max_neighbors_per_site or 16), 32))
    if len(structure) > site_limit:
        raise ValueError(f"local environment analysis is limited to {site_limit} sites on VPS deployments")

    CrystalNN, MinimumDistanceNN = _require_local_env()
    method_name = str(method or "crystal_nn").strip().lower()
    if method_name == "crystal_nn":
        nn = CrystalNN()
        source = "pymatgen.core.local_env.CrystalNN"
    elif method_name in {"minimum_distance", "minimum_distance_nn"}:
        nn = MinimumDistanceNN()
        method_name = "minimum_distance"
        source = "pymatgen.core.local_env.MinimumDistanceNN"
    else:
        raise ValueError("method must be crystal_nn or minimum_distance")

    sites: list[dict[str, Any]] = []
    aggregate: dict[str, dict[str, Any]] = {}
    for index, site in enumerate(structure.sites):
        try:
            nn_info = nn.get_nn_info(structure, index)
        except Exception as exc:
            raise ValueError(f"could not compute local environment for site {index}: {exc}") from exc

        neighbors: list[dict[str, Any]] = []
        neighbor_counts: Counter[str] = Counter()
        effective_cn = 0.0
        for info in nn_info:
            neighbor_site = info.get("site")
            symbol = str(getattr(neighbor_site, "specie", ""))
            weight = float(info.get("weight", 1.0) or 0.0)
            effective_cn += weight
            neighbor_counts[symbol] += 1
            if len(neighbors) < neighbor_limit:
                neighbors.append(
                    {
                        "site_index": _json_int(info.get("site_index")),
                        "species": symbol,
                        "distance_angstrom": _neighbor_distance(structure, index, info),
                        "weight": _round_float(weight, 6),
                    }
                )

        center_symbol = str(site.specie)
        coordination_number = len(nn_info)
        site_payload = {
            "index": index,
            "label": f"{center_symbol}{index + 1}",
            "species": center_symbol,
            "coordination_number": coordination_number,
            "effective_coordination_number": _round_float(effective_cn, 4),
            "coordination_by_element": dict(sorted(neighbor_counts.items())),
            "neighbors": neighbors,
            "neighbors_truncated": len(nn_info) > neighbor_limit,
        }
        sites.append(site_payload)

        bucket = aggregate.setdefault(
            center_symbol,
            {"site_count": 0, "coordination_numbers": [], "effective_coordination_numbers": []},
        )
        bucket["site_count"] += 1
        bucket["coordination_numbers"].append(coordination_number)
        bucket["effective_coordination_numbers"].append(effective_cn)

    species_summary = []
    for species, values in sorted(aggregate.items()):
        cn_values = values["coordination_numbers"]
        ecn_values = values["effective_coordination_numbers"]
        species_summary.append(
            {
                "species": species,
                "site_count": values["site_count"],
                "average_coordination_number": _round_float(sum(cn_values) / len(cn_values), 4),
                "average_effective_coordination_number": _round_float(
                    sum(ecn_values) / len(ecn_values), 4
                ),
                "coordination_number_range": [min(cn_values), max(cn_values)],
            }
        )

    return {
        "success": True,
        "version": "1.0",
        "source": source,
        "engine": "pymatgen",
        "format": fmt,
        "method": method_name,
        "formula": structure.composition.reduced_formula,
        "site_count": len(structure),
        "sites": sites,
        "species_summary": species_summary,
        "parameters": {
            "symprec": float(symprec or 0.1),
            "max_sites": site_limit,
            "max_neighbors_per_site": neighbor_limit,
        },
        "data_quality": {
            "computed_from": f"uploaded_{fmt}",
            "experimental": False,
            "external_database_lookup": False,
        },
        "limitations": [
            "Coordination environments are algorithmic assignments from the supplied coordinates and depend on the selected neighbor method.",
            "Use crystallographic refinement and domain checks before treating local environments as publication-grade bond assignment.",
        ],
    }


def match_structures(
    structure_text_a: Any,
    structure_text_b: Any,
    file_format_a: str | None = "auto",
    file_format_b: str | None = "auto",
    ltol: float = 0.2,
    stol: float = 0.3,
    angle_tol: float = 5.0,
    primitive_cell: bool = True,
    scale: bool = True,
) -> dict[str, Any]:
    """Compare two periodic structures with pymatgen StructureMatcher."""

    text_a = _coerce_structure_text(structure_text_a)
    text_b = _coerce_structure_text(structure_text_b)
    fmt_a = _guess_structure_format(text_a, file_format_a)
    fmt_b = _guess_structure_format(text_b, file_format_b)
    if fmt_a == "xyz" or fmt_b == "xyz":
        raise ValueError("structure matching requires periodic CIF or POSCAR structures")

    structure_a = _load_periodic_structure(text_a, fmt_a)
    structure_b = _load_periodic_structure(text_b, fmt_b)
    max_sites = 256
    if len(structure_a) > max_sites or len(structure_b) > max_sites:
        raise ValueError("structure matching is limited to 256 sites per structure on VPS deployments")

    StructureMatcher = _require_structure_matcher()
    matcher = StructureMatcher(
        ltol=float(ltol or 0.2),
        stol=float(stol or 0.3),
        angle_tol=float(angle_tol or 5.0),
        primitive_cell=bool(primitive_cell),
        scale=bool(scale),
    )

    try:
        match = bool(matcher.fit(structure_a, structure_b))
    except Exception as exc:
        raise ValueError(f"could not compare structures: {exc}") from exc
    try:
        anonymous_match = bool(matcher.fit_anonymous(structure_a, structure_b))
    except Exception:
        anonymous_match = False
    try:
        rms = matcher.get_rms_dist(structure_a, structure_b)
    except Exception:
        rms = None

    rms_payload = None
    if isinstance(rms, (list, tuple)) and rms:
        rms_payload = {
            "rms_distance": _round_float(rms[0], 8),
            "max_distance": _round_float(rms[1] if len(rms) > 1 else None, 8),
        }

    return {
        "success": True,
        "version": "1.0",
        "source": "pymatgen.core.structure_matcher.StructureMatcher",
        "engine": "pymatgen",
        "match": match,
        "anonymous_match": anonymous_match,
        "formula_a": structure_a.composition.reduced_formula,
        "formula_b": structure_b.composition.reduced_formula,
        "site_count_a": len(structure_a),
        "site_count_b": len(structure_b),
        "format_a": fmt_a,
        "format_b": fmt_b,
        "rms": rms_payload,
        "parameters": {
            "ltol": float(ltol or 0.2),
            "stol": float(stol or 0.3),
            "angle_tol": float(angle_tol or 5.0),
            "primitive_cell": bool(primitive_cell),
            "scale": bool(scale),
        },
        "data_quality": {
            "computed_from": "uploaded_structures",
            "experimental": False,
            "external_database_lookup": False,
        },
        "limitations": [
            "Structure matching is a crystallographic equivalence check for the supplied coordinates, not a phase-purity or stability result.",
            "Tolerance choices can change the verdict for distorted, disordered, or partially occupied structures.",
        ],
    }


def quality_check_structure(
    structure_text: Any,
    file_format: str | None = "auto",
    symprec: float = 0.1,
    min_distance_threshold: float = 0.6,
    max_sites: int = 512,
) -> dict[str, Any]:
    """Run lightweight publication-preflight checks on a CIF/POSCAR structure."""

    import numpy as np

    text = _coerce_structure_text(structure_text)
    fmt = _guess_structure_format(text, file_format)
    if fmt == "xyz":
        raise ValueError("structure QC requires a periodic CIF or POSCAR structure")
    site_limit = max(1, min(int(max_sites or 512), 1024))
    threshold = max(0.01, float(min_distance_threshold or 0.6))
    structure = _load_periodic_structure(text, fmt)
    if len(structure) > site_limit:
        raise ValueError(f"structure QC is limited to {site_limit} sites on VPS deployments")

    _, SpacegroupAnalyzer, _ = _require_pymatgen()
    issues: list[dict[str, Any]] = []
    lattice = structure.lattice
    if lattice.volume <= 0:
        issues.append(
            {
                "severity": "error",
                "code": "non_positive_cell_volume",
                "message": "The lattice volume is not positive.",
            }
        )
    for name, value in (
        ("a", lattice.a),
        ("b", lattice.b),
        ("c", lattice.c),
    ):
        if float(value) <= 0:
            issues.append(
                {
                    "severity": "error",
                    "code": "non_positive_lattice_length",
                    "message": f"Lattice length {name} is not positive.",
                }
            )
    for name, value in (
        ("alpha", lattice.alpha),
        ("beta", lattice.beta),
        ("gamma", lattice.gamma),
    ):
        if float(value) <= 0 or float(value) >= 180:
            issues.append(
                {
                    "severity": "error",
                    "code": "invalid_lattice_angle",
                    "message": f"Lattice angle {name} must be between 0 and 180 degrees.",
                }
            )

    unordered_sites = [
        index
        for index, site in enumerate(structure.sites)
        if not bool(getattr(site, "is_ordered", True))
    ]
    if unordered_sites:
        issues.append(
            {
                "severity": "warning",
                "code": "disordered_sites",
                "message": "The structure contains disordered or partial-occupancy sites.",
                "site_indices": unordered_sites[:20],
                "truncated": len(unordered_sites) > 20,
            }
        )

    distance_matrix = np.asarray(structure.distance_matrix, dtype=float)
    np.fill_diagonal(distance_matrix, np.inf)
    min_distance = None
    closest_pair = None
    if distance_matrix.size:
        min_flat = int(np.argmin(distance_matrix))
        row, col = np.unravel_index(min_flat, distance_matrix.shape)
        value = float(distance_matrix[row, col])
        if np.isfinite(value):
            min_distance = round(value, 6)
            closest_pair = {
                "site_indices": [int(row), int(col)],
                "species": [str(structure[row].specie), str(structure[col].specie)],
                "distance_angstrom": min_distance,
            }
            if value < threshold:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "short_interatomic_distance",
                        "message": "The nearest interatomic distance is below the configured threshold.",
                        "threshold_angstrom": threshold,
                        "closest_pair": closest_pair,
                    }
                )

    try:
        analyzer = SpacegroupAnalyzer(structure, symprec=float(symprec or 0.1))
        space_group = {
            "symbol": analyzer.get_space_group_symbol(),
            "number": analyzer.get_space_group_number(),
            "crystal_system": analyzer.get_crystal_system(),
            "symprec": float(symprec or 0.1),
        }
    except Exception as exc:
        space_group = {"error": str(exc), "symprec": float(symprec or 0.1)}
        issues.append(
            {
                "severity": "warning",
                "code": "space_group_assignment_failed",
                "message": str(exc),
            }
        )

    gemmi_summary = _gemmi_cif_summary(text) if fmt == "cif" else None
    if isinstance(gemmi_summary, dict) and gemmi_summary.get("error"):
        issues.append(
            {
                "severity": "warning",
                "code": "gemmi_cif_parse_warning",
                "message": str(gemmi_summary.get("error")),
            }
        )

    errors = sum(1 for issue in issues if issue.get("severity") == "error")
    warnings = sum(1 for issue in issues if issue.get("severity") == "warning")
    return {
        "success": True,
        "version": "1.0",
        "source": "pymatgen_gemmi_structure_qc",
        "engine": "pymatgen",
        "format": fmt,
        "passed": errors == 0,
        "issue_count": len(issues),
        "error_count": errors,
        "warning_count": warnings,
        "issues": issues,
        "formula": structure.composition.reduced_formula,
        "site_count": len(structure),
        "density_g_cm3": round(float(structure.density), 6),
        "min_interatomic_distance_angstrom": min_distance,
        "closest_pair": closest_pair,
        "space_group": space_group,
        "cif_syntax": gemmi_summary,
        "parameters": {
            "symprec": float(symprec or 0.1),
            "min_distance_threshold": threshold,
            "max_sites": site_limit,
        },
        "limitations": [
            "Structure QC detects common parsing, geometry, and symmetry red flags only; it does not validate refinement quality, phase purity, or thermodynamic stability.",
        ],
    }


def transform_structure(
    structure_text: Any,
    file_format: str | None = "auto",
    output_format: str = "cif",
    make_primitive: bool = False,
    make_conventional: bool = False,
    supercell_matrix: Any = None,
    symprec: float = 0.1,
    max_sites: int = 512,
) -> dict[str, Any]:
    """Convert CIF/POSCAR structures and optionally build primitive/conventional/supercell forms."""

    text = _coerce_structure_text(structure_text)
    fmt = _guess_structure_format(text, file_format)
    if fmt == "xyz":
        raise ValueError("structure conversion requires a periodic CIF or POSCAR structure")
    output = str(output_format or "cif").strip().lower()
    aliases = {"vasp": "poscar", "contcar": "poscar", "cif": "cif", "poscar": "poscar", "json": "json"}
    if output not in aliases:
        raise ValueError("output_format must be cif, poscar, or json")
    output = aliases[output]
    site_limit = max(1, min(int(max_sites or 512), 2048))

    _, SpacegroupAnalyzer, _ = _require_pymatgen()
    structure = _load_periodic_structure(text, fmt)
    input_site_count = len(structure)
    operations: list[str] = []
    working = structure.copy()

    if make_primitive:
        try:
            working = SpacegroupAnalyzer(working, symprec=float(symprec or 0.1)).get_primitive_standard_structure()
            operations.append("primitive_standard_structure")
        except Exception as exc:
            raise ValueError(f"could not build primitive structure: {exc}") from exc
    if make_conventional:
        try:
            working = SpacegroupAnalyzer(working, symprec=float(symprec or 0.1)).get_conventional_standard_structure()
            operations.append("conventional_standard_structure")
        except Exception as exc:
            raise ValueError(f"could not build conventional structure: {exc}") from exc

    if supercell_matrix is not None:
        if (
            isinstance(supercell_matrix, list)
            and len(supercell_matrix) == 3
            and all(not isinstance(item, list) for item in supercell_matrix)
        ):
            matrix = [int(item) for item in supercell_matrix]
        elif (
            isinstance(supercell_matrix, list)
            and len(supercell_matrix) == 3
            and all(isinstance(row, list) and len(row) == 3 for row in supercell_matrix)
        ):
            matrix = [[int(item) for item in row] for row in supercell_matrix]
        else:
            raise ValueError("supercell_matrix must be [a,b,c] or a 3x3 integer matrix")
        try:
            working.make_supercell(matrix)
            operations.append("supercell")
        except Exception as exc:
            raise ValueError(f"could not build supercell: {exc}") from exc

    if len(working) > site_limit:
        raise ValueError(f"transformed structure has {len(working)} sites; VPS limit is {site_limit}")

    if output == "json":
        output_text = json.dumps(working.as_dict(), ensure_ascii=False)
    else:
        output_text = str(working.to(fmt=output))
    return {
        "success": True,
        "version": "1.0",
        "source": "pymatgen_structure_transform",
        "engine": "pymatgen",
        "input_format": fmt,
        "output_format": output,
        "operations": operations or ["format_conversion"],
        "input_formula": structure.composition.reduced_formula,
        "output_formula": working.composition.reduced_formula,
        "input_site_count": input_site_count,
        "output_site_count": len(working),
        "structure_text": output_text,
        "parameters": {
            "symprec": float(symprec or 0.1),
            "max_sites": site_limit,
            "make_primitive": bool(make_primitive),
            "make_conventional": bool(make_conventional),
            "supercell_matrix": supercell_matrix,
        },
        "limitations": [
            "Structure conversion preserves the supplied coordinates and symmetry interpretation; it does not relax or validate the structure energetically.",
        ],
    }


def simulate_xrd(
    structure_text: Any,
    file_format: str | None = "auto",
    wavelength: str = "CuKa",
    two_theta_min: float = 5.0,
    two_theta_max: float = 90.0,
    min_relative_intensity: float = 1.0,
    max_peaks: int = 120,
) -> dict[str, Any]:
    """Simulate a powder XRD stick pattern from CIF/POSCAR text with pymatgen."""
    text = _coerce_structure_text(structure_text)
    fmt = _guess_structure_format(text, file_format)
    if fmt == "xyz":
        raise ValueError("XRD simulation requires a periodic CIF or POSCAR structure")

    min_angle = float(two_theta_min)
    max_angle = float(two_theta_max)
    if min_angle < 0 or max_angle <= min_angle or max_angle > 180:
        raise ValueError("two theta range must satisfy 0 <= min < max <= 180")
    min_intensity = max(0.0, float(min_relative_intensity or 0.0))
    peak_limit = max(1, min(300, int(max_peaks or 120)))

    _, _, XRDCalculator = _require_pymatgen()
    structure = _load_periodic_structure(text, fmt)
    calculator = XRDCalculator(wavelength=wavelength or "CuKa")
    pattern = calculator.get_pattern(structure, two_theta_range=(min_angle, max_angle))

    peaks: list[dict[str, Any]] = []
    for index, (two_theta, intensity, d_spacing) in enumerate(
        zip(pattern.x, pattern.y, pattern.d_hkls)
    ):
        if float(intensity) < min_intensity:
            continue
        hkl_items = [
            {
                "hkl": [int(value) for value in item.get("hkl", ())],
                "multiplicity": int(item.get("multiplicity", 1)),
            }
            for item in pattern.hkls[index]
        ]
        peaks.append(
            {
                "two_theta": round(float(two_theta), 6),
                "intensity": round(float(intensity), 6),
                "d_spacing": round(float(d_spacing), 6),
                "hkls": hkl_items,
                "hkl_label": _format_hkl_label(hkl_items),
            }
        )
        if len(peaks) >= peak_limit:
            break

    annotation_indices = set(_select_xrd_annotation_indices(peaks))
    annotations = [
        {
            "peak_index": index,
            "x": peaks[index]["two_theta"],
            "y": peaks[index]["intensity"],
            "label": peaks[index].get("hkl_label") or f'{peaks[index]["two_theta"]:.2f}',
        }
        for index in sorted(annotation_indices)
    ]

    return {
        "success": True,
        "version": "2.0",
        "source": "pymatgen.analysis.diffraction.xrd.XRDCalculator",
        "engine": "pymatgen",
        "format": fmt,
        "formula": structure.composition.reduced_formula,
        "wavelength": wavelength or "CuKa",
        "two_theta_range": [min_angle, max_angle],
        "min_relative_intensity": min_intensity,
        "peak_count": len(peaks),
        "peaks": peaks,
        "visualization": {
            "type": "xrd_stick_pattern",
            "x_axis": "2theta_deg",
            "y_axis": "relative_intensity",
            "label_policy": {
                "mode": "selected_major_peaks",
                "max_annotations": 12,
                "min_relative_intensity": 8.0,
                "reason": "Avoid overlapping HKL labels on dense powder XRD patterns.",
            },
            "series": [
                {
                    "x": peak["two_theta"],
                    "y": peak["intensity"],
                    "label": peak["hkl_label"] if index in annotation_indices else "",
                }
                for index, peak in enumerate(peaks)
            ],
            "annotations": annotations,
        },
        "data_quality": {
            "computed_from": f"uploaded_{fmt}",
            "experimental": False,
        },
        "limitations": [
            "Theoretical XRD assumes the provided crystal structure and does not model texture, strain, crystallite size, or instrument broadening.",
            "Use experimental calibration and Rietveld refinement for publication-grade phase quantification.",
        ],
    }


def simulate_and_match_xrd(
    structure_text: Any,
    observed_peaks: Any,
    file_format: str | None = "auto",
    tolerance_two_theta: float = 0.25,
    wavelength: str = "CuKa",
    two_theta_min: float = 5.0,
    two_theta_max: float = 90.0,
    min_relative_intensity: float = 5.0,
) -> dict[str, Any]:
    """Simulate XRD from a structure and match it against observed peaks."""
    from .xrd_matching import match_xrd_peaks

    simulated = simulate_xrd(
        structure_text,
        file_format=file_format,
        wavelength=wavelength,
        two_theta_min=two_theta_min,
        two_theta_max=two_theta_max,
        min_relative_intensity=min_relative_intensity,
    )
    match = match_xrd_peaks(
        observed_peaks=observed_peaks,
        reference_peaks=simulated["peaks"],
        tolerance_two_theta=tolerance_two_theta,
    )
    return {
        "success": True,
        "version": "2.0",
        "source": "gvim_materials_xrd_simulate_match",
        "engine": "pymatgen",
        "simulation": simulated,
        "match": match,
        "interpretation_hints": [
            "High match score supports consistency with the supplied structure but does not prove single-phase purity.",
            "Extra observed peaks may indicate impurities, secondary phases, or unmodeled instrument artifacts.",
        ],
    }
