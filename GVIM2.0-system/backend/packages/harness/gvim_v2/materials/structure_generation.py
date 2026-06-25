"""Package-backed crystal description and candidate generation tools."""

from __future__ import annotations

import hashlib
import warnings
from typing import Any

from .errors import FormulaError, MaterialsDependencyError
from .structure_analysis import (
    _coerce_structure_text,
    _guess_structure_format,
    _load_periodic_structure,
    _round_float,
)


def _require_robocrys():
    try:
        from robocrys import StructureCondenser, StructureDescriber
    except Exception as exc:  # pragma: no cover - depends on deployment env
        raise MaterialsDependencyError(
            "robocrys is required for automated crystal-structure descriptions"
        ) from exc
    return StructureCondenser, StructureDescriber


def _require_pyxtal():
    try:
        from pyxtal import pyxtal
        from pyxtal.symmetry import Group
    except Exception as exc:  # pragma: no cover - depends on deployment env
        raise MaterialsDependencyError(
            "pyxtal is required for symmetry-constrained crystal candidate generation"
        ) from exc
    return pyxtal, Group


def _require_pymatgen_generation():
    try:
        from pymatgen.core import Composition
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    except Exception as exc:  # pragma: no cover - depends on deployment env
        raise MaterialsDependencyError(
            "pymatgen is required to prepare formulas and summarize generated structures"
        ) from exc
    return Composition, SpacegroupAnalyzer


def _bounded_int(value: Any, default: int, minimum: int, maximum: int, label: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed < minimum:
        raise FormulaError(f"{label} must be at least {minimum}")
    return min(parsed, maximum)


def _space_group_payload(structure: Any, symprec: float) -> dict[str, Any]:
    _, SpacegroupAnalyzer = _require_pymatgen_generation()
    try:
        analyzer = SpacegroupAnalyzer(structure, symprec=float(symprec or 0.1))
        return {
            "symbol": analyzer.get_space_group_symbol(),
            "number": analyzer.get_space_group_number(),
            "crystal_system": analyzer.get_crystal_system(),
            "hall": analyzer.get_hall(),
            "symprec": float(symprec or 0.1),
            "engine": "spglib_via_pymatgen",
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "symprec": float(symprec or 0.1),
            "engine": "spglib_via_pymatgen",
        }


def _lattice_payload(structure: Any) -> dict[str, float | None]:
    lattice = structure.lattice
    return {
        "a": _round_float(lattice.a, 6),
        "b": _round_float(lattice.b, 6),
        "c": _round_float(lattice.c, 6),
        "alpha": _round_float(lattice.alpha, 6),
        "beta": _round_float(lattice.beta, 6),
        "gamma": _round_float(lattice.gamma, 6),
        "volume": _round_float(lattice.volume, 6),
    }


def _captured_warning_messages(captured: list[warnings.WarningMessage]) -> list[str]:
    messages: list[str] = []
    seen: set[str] = set()
    for item in captured:
        message = str(item.message).strip()
        if message and message not in seen:
            messages.append(message)
            seen.add(message)
    return messages[:8]


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _robocrys_components(condensed: dict[str, Any]) -> list[dict[str, Any]]:
    components = condensed.get("components")
    if not isinstance(components, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key, component in components.items():
        if not isinstance(component, dict):
            continue
        sites = component.get("sites")
        rows.append(
            {
                "id": str(key),
                "formula": _json_safe(component.get("formula")),
                "dimensionality": _json_safe(component.get("dimensionality")),
                "site_count": len(sites) if isinstance(sites, list) else None,
                "molecule_name": _json_safe(component.get("molecule_name")),
            }
        )
    return rows[:16]


def describe_structure_with_robocrys(
    structure_text: Any,
    file_format: str | None = "auto",
    symprec: float = 0.1,
    max_sites: int = 256,
    include_mineral_match: bool = False,
) -> dict[str, Any]:
    """Describe a periodic CIF/POSCAR structure with robocrys.

    Oxidation-state text is intentionally disabled. The service reports package
    warnings so callers can see when the input lacks oxidation states or other
    information needed by robocrys' neighbor analysis.
    """
    text = _coerce_structure_text(structure_text)
    fmt = _guess_structure_format(text, file_format)
    if fmt not in {"cif", "poscar"}:
        raise FormulaError("robocrys structure description requires periodic CIF or POSCAR text")

    site_limit = _bounded_int(max_sites, 256, 1, 512, "max_sites")
    structure = _load_periodic_structure(text, fmt)
    if len(structure) > site_limit:
        raise FormulaError(f"robocrys description is limited to {site_limit} sites on VPS deployments")

    StructureCondenser, StructureDescriber = _require_robocrys()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        condenser = StructureCondenser(
            use_conventional_cell=True,
            use_symmetry_equivalent_sites=True,
            symprec=float(symprec or 0.1),
        )
        condensed = condenser.condense_structure(structure)
        describer = StructureDescriber(
            describe_mineral=bool(include_mineral_match),
            describe_oxidation_states=False,
            fmt="raw",
        )
        description = describer.describe(condensed)

    mineral_match = condensed.get("mineral") if include_mineral_match else None
    return {
        "success": True,
        "version": "1.0",
        "source": "robocrys.StructureCondenser+StructureDescriber",
        "engine": "robocrys",
        "format": fmt,
        "formula": structure.composition.formula,
        "reduced_formula": structure.composition.reduced_formula,
        "site_count": len(structure),
        "density_g_cm3": _round_float(structure.density, 6),
        "space_group": _space_group_payload(structure, float(symprec or 0.1)),
        "lattice": _lattice_payload(structure),
        "description": str(description or "").strip(),
        "condensed_summary": {
            "formula": _json_safe(condensed.get("formula")),
            "space_group_symbol": _json_safe(condensed.get("spg_symbol")),
            "crystal_system": _json_safe(condensed.get("crystal_system")),
            "dimensionality": _json_safe(condensed.get("dimensionality")),
            "component_makeup": _json_safe(condensed.get("component_makeup")),
            "components": _robocrys_components(condensed),
            "mineral_match": _json_safe(mineral_match),
        },
        "warnings": _captured_warning_messages(captured),
        "parameters": {
            "symprec": float(symprec or 0.1),
            "max_sites": site_limit,
            "include_mineral_match": bool(include_mineral_match),
            "describe_oxidation_states": False,
        },
        "data_quality": {
            "computed_from": "uploaded_periodic_structure",
            "experimental": False,
            "external_database_lookup": False,
            "oxidation_states_inferred": False,
            "package_generated_description": True,
        },
        "limitations": [
            "robocrys generates an automated text condensation from the supplied structure; it is not DFT, experimental validation, phase-stability evidence, or synthesis evidence.",
            "This service does not infer oxidation states. Bond and topology text depends on the oxidation states and coordinates present in the input structure.",
            "Mineral or structure-type matching is returned only when requested and should be treated as package metadata.",
        ],
    }


def _normalize_space_group(space_group: Any) -> int | str:
    if isinstance(space_group, int):
        return space_group
    text = str(space_group or "").strip()
    if not text:
        raise FormulaError("space_group is required for PyXtal generation")
    if text.isdigit():
        return int(text)
    return text


def _integer_formula_species(formula: Any) -> tuple[str, list[str], list[int]]:
    Composition, _ = _require_pymatgen_generation()
    text = str(formula or "").strip()
    if not text:
        raise FormulaError("formula is required for PyXtal generation")
    try:
        composition = Composition(text)
        integer_formula, _factor = composition.get_integer_formula_and_factor()
        integer_composition = Composition(integer_formula)
    except Exception as exc:
        raise FormulaError(f"invalid formula for PyXtal generation: {text}") from exc

    species: list[str] = []
    counts: list[int] = []
    for element in integer_composition.elements:
        amount = integer_composition[element]
        rounded = int(round(float(amount)))
        if rounded <= 0 or abs(float(amount) - rounded) > 1e-8:
            raise FormulaError("PyXtal generation requires an integer composition")
        species.append(element.symbol)
        counts.append(rounded)
    return integer_composition.reduced_formula, species, counts


def _compatible_num_ions(
    *,
    group: Any,
    base_counts: list[int],
    formula_units: Any,
    max_formula_units: int,
    max_sites: int,
) -> tuple[int, list[int], bool]:
    if formula_units is not None and formula_units != "":
        unit_count = _bounded_int(formula_units, 1, 1, max_formula_units, "formula_units")
        num_ions = [count * unit_count for count in base_counts]
        if sum(num_ions) > max_sites:
            raise FormulaError(f"requested formula_units produce {sum(num_ions)} sites; max_sites is {max_sites}")
        compatible, has_freedom = group.check_compatible(num_ions)
        if not compatible:
            raise FormulaError(
                f"composition {num_ions} is not Wyckoff-compatible with space group {group.number}"
            )
        return unit_count, num_ions, bool(has_freedom)

    for unit_count in range(1, max_formula_units + 1):
        num_ions = [count * unit_count for count in base_counts]
        if sum(num_ions) > max_sites:
            break
        compatible, has_freedom = group.check_compatible(num_ions)
        if compatible:
            return unit_count, num_ions, bool(has_freedom)
    raise FormulaError(
        f"no Wyckoff-compatible integer formula-unit count found within {max_formula_units} units and {max_sites} sites"
    )


def _structure_output(structure: Any, output_format: str) -> str | dict[str, Any]:
    fmt = str(output_format or "cif").strip().lower()
    if fmt in {"cif", "poscar"}:
        return structure.to(fmt=fmt)
    if fmt == "json":
        return structure.as_dict()
    raise FormulaError("output_format must be cif, poscar, or json")


def generate_pyxtal_structures(
    formula: Any,
    space_group: Any,
    *,
    dimensionality: int = 3,
    candidate_count: int = 1,
    formula_units: int | None = None,
    max_formula_units: int = 12,
    max_sites: int = 128,
    max_attempts: int = 30,
    seed: int | None = None,
    output_format: str = "cif",
    symprec: float = 0.1,
) -> dict[str, Any]:
    """Generate symmetry-constrained crystal candidates with PyXtal."""
    if int(dimensionality or 3) != 3:
        raise FormulaError("PyXtal generation currently supports 3D periodic crystals only")

    pyxtal_cls, Group = _require_pyxtal()
    Composition, SpacegroupAnalyzer = _require_pymatgen_generation()
    reduced_formula, species, base_counts = _integer_formula_species(formula)
    try:
        group = Group(_normalize_space_group(space_group))
    except Exception as exc:
        raise FormulaError(f"invalid or unsupported space_group for PyXtal: {space_group}") from exc

    requested_candidates = _bounded_int(candidate_count, 1, 1, 5, "candidate_count")
    formula_unit_limit = _bounded_int(max_formula_units, 12, 1, 24, "max_formula_units")
    site_limit = _bounded_int(max_sites, 128, 1, 256, "max_sites")
    pyxtal_max_count = _bounded_int(max_attempts, 30, 1, 100, "max_attempts")
    selected_units, num_ions, has_freedom = _compatible_num_ions(
        group=group,
        base_counts=base_counts,
        formula_units=formula_units,
        max_formula_units=formula_unit_limit,
        max_sites=site_limit,
    )

    fmt = str(output_format or "cif").strip().lower()
    candidates: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_hashes: set[str] = set()
    try:
        base_seed = int(seed) if seed is not None and seed != "" else 20260501
    except (TypeError, ValueError) as exc:
        raise FormulaError("seed must be an integer when provided") from exc
    outer_trials = max(requested_candidates * 4, requested_candidates)

    for trial_index in range(outer_trials):
        if len(candidates) >= requested_candidates:
            break
        trial_seed = base_seed + trial_index
        try:
            xtal = pyxtal_cls()
            xtal.from_random(
                dim=3,
                group=group.number,
                species=species,
                numIons=num_ions,
                conventional=True,
                max_count=pyxtal_max_count,
                seed=trial_seed,
            )
            structure = xtal.to_pymatgen()
            if len(structure) > site_limit:
                raise FormulaError(f"generated structure has {len(structure)} sites; max_sites is {site_limit}")
            structure_text = _structure_output(structure, fmt)
            hash_input = structure.to(fmt="cif").encode("utf-8", errors="ignore")
            digest = hashlib.sha256(hash_input).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            analyzer = SpacegroupAnalyzer(structure, symprec=float(symprec or 0.1))
            candidates.append(
                {
                    "index": len(candidates) + 1,
                    "seed": trial_seed,
                    "formula": structure.composition.reduced_formula,
                    "full_formula": structure.composition.formula,
                    "site_count": len(structure),
                    "density_g_cm3": _round_float(structure.density, 6),
                    "lattice": _lattice_payload(structure),
                    "space_group": {
                        "symbol": analyzer.get_space_group_symbol(),
                        "number": analyzer.get_space_group_number(),
                        "crystal_system": analyzer.get_crystal_system(),
                        "symprec": float(symprec or 0.1),
                        "engine": "spglib_via_pymatgen",
                    },
                    "requested_space_group": {
                        "symbol": group.symbol,
                        "number": group.number,
                    },
                    "formula_units": selected_units,
                    "num_ions": [int(item) for item in num_ions],
                    "has_free_wyckoff_parameters": has_freedom,
                    "structure_hash": digest[:16],
                    "output_format": fmt,
                    "structure_text": structure_text,
                }
            )
        except Exception as exc:
            if len(errors) < 8:
                errors.append(f"seed {trial_seed}: {exc}")

    if not candidates:
        detail = "; ".join(errors[:3]) if errors else "PyXtal did not return a valid candidate"
        raise FormulaError(f"PyXtal generation failed: {detail}")

    return {
        "success": True,
        "version": "1.0",
        "source": "pyxtal.pyxtal.from_random",
        "engine": "pyxtal",
        "formula": str(formula).strip(),
        "reduced_formula": Composition(reduced_formula).reduced_formula,
        "species": species,
        "base_counts": base_counts,
        "space_group": {
            "symbol": group.symbol,
            "number": group.number,
        },
        "formula_units": selected_units,
        "num_ions": [int(item) for item in num_ions],
        "wyckoff_compatible": True,
        "generated_count": len(candidates),
        "candidate_count": requested_candidates,
        "candidates": candidates,
        "generation_errors": errors,
        "parameters": {
            "dimensionality": 3,
            "candidate_count": requested_candidates,
            "max_formula_units": formula_unit_limit,
            "max_sites": site_limit,
            "max_attempts": pyxtal_max_count,
            "seed": base_seed,
            "output_format": fmt,
            "symprec": float(symprec or 0.1),
        },
        "data_quality": {
            "computed_from": "pyxtal_random_crystal_generation",
            "symmetry_constraints_checked_by": "pyxtal.symmetry.Group.check_compatible",
            "experimental": False,
            "external_database_lookup": False,
            "energy_optimized": False,
            "stability_inference": False,
            "synthesis_inference": False,
        },
        "limitations": [
            "PyXtal returns symmetry-compatible randomly generated crystal candidates only.",
            "Generated candidates are not energy minimized and do not prove thermodynamic stability, phase purity, synthesizability, or experimental existence.",
            "Use downstream relaxation, DFT, diffraction comparison, or database evidence before making research claims.",
        ],
    }
