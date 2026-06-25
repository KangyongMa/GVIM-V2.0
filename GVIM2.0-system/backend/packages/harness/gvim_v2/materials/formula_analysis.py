"""Package-backed materials formula analysis.

Formula parsing and composition descriptors come from pymatgen. The module
does not assign material applications, risk classes, or rankings from formula
patterns because those claims require structure, property, database, or
literature evidence.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .errors import FormulaError, MaterialsDependencyError


def _require_pymatgen_formula():
    try:
        from pymatgen.core import Composition, Element
    except Exception as exc:  # pragma: no cover - depends on deployment env
        raise MaterialsDependencyError(
            "pymatgen is required for materials formula analysis"
        ) from exc
    return Composition, Element


def _composition_from_formula(formula: Any):
    Composition, _ = _require_pymatgen_formula()
    cleaned = str(formula or "").strip()
    if not cleaned:
        raise FormulaError("formula is required")
    if len(cleaned) > 500:
        raise FormulaError("formula is limited to 500 characters")
    try:
        composition = Composition(cleaned)
    except Exception as exc:
        raise FormulaError(f"invalid formula: {cleaned}") from exc
    if not composition.elements:
        raise FormulaError("formula did not contain elements")
    return composition


def parse_formula(formula: Any) -> OrderedDict[str, float]:
    """Parse a formula with pymatgen and return element amounts."""
    composition = _composition_from_formula(formula)
    return OrderedDict(
        (str(element), float(amount))
        for element, amount in composition.get_el_amt_dict().items()
        if float(amount) != 0.0
    )


def _composition_from_counts(counts: OrderedDict[str, float]):
    Composition, _ = _require_pymatgen_formula()
    try:
        return Composition(dict(counts))
    except Exception as exc:
        raise FormulaError("invalid parsed formula composition") from exc


def molar_mass_from_counts(counts: OrderedDict[str, float]) -> float:
    """Compute molar mass from parsed element counts using pymatgen elements."""
    _, Element = _require_pymatgen_formula()
    mass = 0.0
    for element, amount in counts.items():
        try:
            mass += float(Element(element).atomic_mass) * float(amount)
        except Exception as exc:
            raise FormulaError(f"unknown element symbol: {element}") from exc
    return mass


def _format_formula(counts: OrderedDict[str, float | int]) -> str:
    composition = _composition_from_counts(
        OrderedDict((element, float(amount)) for element, amount in counts.items())
    )
    return composition.formula.replace(" ", "")


def _reduced_integer_counts(counts: OrderedDict[str, float]) -> OrderedDict[str, float]:
    composition = _composition_from_counts(counts).reduced_composition
    return OrderedDict(
        (str(element), float(amount))
        for element, amount in composition.get_el_amt_dict().items()
    )


def _round_float(value: Any, digits: int = 6) -> float | None:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def analyze_formula(formula: Any) -> dict[str, Any]:
    composition = _composition_from_formula(formula)
    _, Element = _require_pymatgen_formula()
    counts = OrderedDict(
        (str(element), float(amount))
        for element, amount in composition.get_el_amt_dict().items()
    )
    reduced = OrderedDict(
        (str(element), float(amount))
        for element, amount in composition.reduced_composition.get_el_amt_dict().items()
    )
    total_atoms = float(composition.num_atoms)
    molar_mass = float(composition.weight)

    element_items: list[dict[str, Any]] = []
    weighted_atomic_numbers = 0.0
    for symbol, amount in counts.items():
        element = Element(symbol)
        atomic_mass = float(element.atomic_mass)
        atomic_number = int(element.Z)
        weighted_atomic_numbers += atomic_number * amount
        element_items.append(
            {
                "symbol": symbol,
                "amount": round(amount, 8),
                "atomic_number": atomic_number,
                "atomic_mass_g_mol": round(atomic_mass, 6),
                "weight_fraction": round((atomic_mass * amount) / molar_mass, 8)
                if molar_mass
                else None,
            }
        )

    return {
        "success": True,
        "version": "2.0",
        "source": "pymatgen.core.Composition",
        "engine": "pymatgen",
        "formula": str(formula or "").strip(),
        "normalized_formula": composition.formula.replace(" ", ""),
        "reduced_formula": composition.reduced_formula,
        "composition": dict(counts),
        "reduced_composition": dict(reduced),
        "descriptors": {
            "element_count": len(counts),
            "total_atoms_per_formula": round(total_atoms, 8),
            "molar_mass_g_mol": round(molar_mass, 6),
            "average_atomic_number": round(weighted_atomic_numbers / total_atoms, 6)
            if total_atoms
            else None,
            "average_electronegativity": _round_float(
                getattr(composition, "average_electroneg", None), 6
            ),
            "anonymized_formula": composition.anonymized_formula,
            "chemical_system": composition.chemical_system,
        },
        "elements": element_items,
        "data_quality": {
            "computed_from": "chemical_formula",
            "experimental": False,
            "external_database_lookup": False,
            "application_inference": False,
        },
        "next_actions": [
            "Provide a CIF/POSCAR structure to compute density, symmetry, and theoretical XRD.",
            "Use Materials Project/COD or laboratory data before claiming stability, band gap, conductivity, or application fit.",
            "Compare computed or experimental properties against the target use case.",
        ],
        "limitations": [
            "Composition analysis does not prove crystal structure, phase purity, oxidation states, phase stability, or synthesizability.",
            "No material application or risk ranking is inferred from formula alone.",
        ],
    }


def screen_formulas(formulas: list[str], target_application: str = "") -> dict[str, Any]:
    if not isinstance(formulas, list) or not formulas:
        raise FormulaError("formulas must be a non-empty list")
    if len(formulas) > 50:
        raise FormulaError("formula screening is limited to 50 formulas per request")

    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for formula in formulas:
        try:
            results.append(analyze_formula(str(formula)))
        except FormulaError as exc:
            errors.append({"formula": str(formula), "error": str(exc)})

    payload: dict[str, Any] = {
        "success": True,
        "version": "2.0",
        "source": "pymatgen.core.Composition",
        "engine": "pymatgen",
        "target_application": target_application or "",
        "screening_method": "parse_and_compute_composition_only",
        "ranking_method": "none_without_property_or_database_evidence",
        "count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
        "limitations": [
            "Candidate order is the submitted order; formulas are not ranked by application fit.",
            "Application screening requires measured properties, computed descriptors, database records, or a validated model.",
        ],
    }
    if str(target_application or "").strip():
        payload["evidence_gap"] = (
            "Target application was recorded but not used for ranking because formula-only "
            "composition is insufficient evidence."
        )
    return payload
