"""Package-backed precursor stoichiometry planning for materials workflows."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

import numpy as np

from .errors import FormulaError
from .formula_analysis import molar_mass_from_counts, parse_formula


VOLATILE_OR_AMBIENT_ELEMENTS = {"H", "C", "N", "O"}


def _molar_mass(counts: OrderedDict[str, float]) -> float:
    return molar_mass_from_counts(counts)


def _normalize_precursor(item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        formula = item.strip()
        return {
            "formula": formula,
            "label": formula,
            "purity": 1.0,
            "excess_fraction": 0.0,
        }
    if isinstance(item, dict):
        formula = str(item.get("formula") or "").strip()
        if not formula:
            raise FormulaError("each precursor requires a formula")
        try:
            purity = float(item.get("purity", 1.0) or 1.0)
            excess_fraction = float(item.get("excess_fraction", item.get("excess", 0.0)) or 0.0)
        except (TypeError, ValueError) as exc:
            raise FormulaError("precursor purity and excess_fraction must be numeric") from exc
        if purity <= 0 or purity > 1.5:
            raise FormulaError("precursor purity must be between 0 and 1.5")
        if excess_fraction < -0.5 or excess_fraction > 2.0:
            raise FormulaError("precursor excess_fraction must be between -0.5 and 2.0")
        return {
            "formula": formula,
            "label": str(item.get("label") or formula).strip(),
            "purity": purity,
            "excess_fraction": excess_fraction,
        }
    raise FormulaError("precursors must be formula strings or objects")


def _select_basis_elements(
    target_counts: OrderedDict[str, float],
    precursor_counts: list[OrderedDict[str, float]],
    basis_elements: Any,
) -> list[str]:
    if basis_elements:
        selected = [str(item).strip() for item in basis_elements if str(item).strip()]
    else:
        selected = [element for element in target_counts if element not in VOLATILE_OR_AMBIENT_ELEMENTS]
        if not selected:
            selected = list(target_counts)
    unknown = [element for element in selected if element not in target_counts]
    if unknown:
        raise FormulaError(f"basis elements are not in target formula: {', '.join(unknown)}")
    missing = [
        element
        for element in selected
        if not any(counts.get(element, 0.0) > 0 for counts in precursor_counts)
    ]
    if missing:
        raise FormulaError(f"basis elements are not supplied by precursors: {', '.join(missing)}")
    return selected


def _solve_coefficients(
    target_counts: OrderedDict[str, float],
    precursor_counts: list[OrderedDict[str, float]],
    basis_elements: list[str],
) -> tuple[np.ndarray, float]:
    matrix = np.array(
        [[counts.get(element, 0.0) for counts in precursor_counts] for element in basis_elements],
        dtype=float,
    )
    target = np.array([target_counts.get(element, 0.0) for element in basis_elements], dtype=float)
    coefficients, *_ = np.linalg.lstsq(matrix, target, rcond=None)
    coefficients[np.abs(coefficients) < 1e-10] = 0.0
    if np.any(coefficients < -1e-8):
        raise FormulaError(
            "precursor set requires negative coefficients; provide a different precursor list or basis_elements"
        )
    coefficients = np.maximum(coefficients, 0.0)
    residual = float(np.linalg.norm(matrix @ coefficients - target))
    target_norm = float(np.linalg.norm(target)) or 1.0
    relative_residual = residual / target_norm
    if relative_residual > 0.05:
        raise FormulaError(
            "precursor stoichiometry could not match selected basis elements within 5% residual"
        )
    return coefficients, relative_residual


def plan_precursors(
    target_formula: Any,
    target_mass_g: Any,
    precursors: Any,
    basis_elements: Any = None,
) -> dict[str, Any]:
    """Plan precursor masses for a target material formula.

    This is a deterministic stoichiometry aid, not a synthesis guarantee. By
    default it balances non-volatile framework/cation elements and reports O/H/C/N
    as oxygen/volatile balance because solid-state precursors often release CO2,
    NH3, H2O, or exchange oxygen with atmosphere.
    """
    formula = str(target_formula or "").strip()
    if not formula:
        raise FormulaError("target_formula is required")
    try:
        target_mass = float(target_mass_g)
    except (TypeError, ValueError) as exc:
        raise FormulaError("target_mass_g must be numeric") from exc
    if target_mass <= 0 or target_mass > 1_000_000:
        raise FormulaError("target_mass_g must be positive and below 1,000,000 g")
    if not isinstance(precursors, list) or not precursors:
        raise FormulaError("precursors must be a non-empty list")
    if len(precursors) > 20:
        raise FormulaError("precursor planning is limited to 20 precursors")

    target_counts = parse_formula(formula)
    normalized_precursors = [_normalize_precursor(item) for item in precursors]
    precursor_counts = [parse_formula(item["formula"]) for item in normalized_precursors]
    basis = _select_basis_elements(target_counts, precursor_counts, basis_elements)
    coefficients, relative_residual = _solve_coefficients(target_counts, precursor_counts, basis)

    target_molar_mass = _molar_mass(target_counts)
    target_moles = target_mass / target_molar_mass
    table: list[dict[str, Any]] = []
    supplied_per_formula: dict[str, float] = {}
    for item, counts, coefficient in zip(normalized_precursors, precursor_counts, coefficients):
        coefficient_value = float(coefficient)
        molar_mass = _molar_mass(counts)
        theoretical_moles = coefficient_value * target_moles
        theoretical_mass = theoretical_moles * molar_mass
        weigh_mass = theoretical_mass * (1.0 + item["excess_fraction"]) / item["purity"]
        for element, amount in counts.items():
            supplied_per_formula[element] = supplied_per_formula.get(element, 0.0) + amount * coefficient_value
        table.append(
            {
                "label": item["label"],
                "formula": item["formula"],
                "coefficient_per_target_formula": round(coefficient_value, 8),
                "molar_mass_g_mol": round(molar_mass, 6),
                "theoretical_moles": round(theoretical_moles, 8),
                "theoretical_mass_g": round(theoretical_mass, 6),
                "purity": item["purity"],
                "excess_fraction": item["excess_fraction"],
                "weigh_mass_g": round(weigh_mass, 6),
            }
        )

    element_balance = []
    all_elements = sorted(set(target_counts) | set(supplied_per_formula))
    for element in all_elements:
        target_amount = target_counts.get(element, 0.0)
        supplied_amount = supplied_per_formula.get(element, 0.0)
        delta = supplied_amount - target_amount
        element_balance.append(
            {
                "element": element,
                "target_per_formula": round(target_amount, 8),
                "precursor_supplied_per_formula": round(supplied_amount, 8),
                "delta_per_formula": round(delta, 8),
                "role": "basis_balanced" if element in basis else "volatile_or_unconstrained",
            }
        )

    return {
        "success": True,
        "version": "2.0",
        "source": "gvim_materials_precursor_planning",
        "engine": "pymatgen.core.Composition + numpy.linalg.lstsq",
        "target_formula": formula,
        "target_mass_g": target_mass,
        "target_molar_mass_g_mol": round(target_molar_mass, 6),
        "target_moles": round(target_moles, 8),
        "basis_elements": basis,
        "basis_relative_residual": round(relative_residual, 8),
        "stoichiometry_residual_fraction": round(relative_residual, 8),
        "precursors": table,
        "element_balance": element_balance,
        "data_quality": {
            "computed_from": "formula_stoichiometry",
            "experimental": False,
        },
        "visualization": {
            "type": "precursor_mass_bar",
            "x_axis": "precursor",
            "y_axis": "weigh_mass_g",
            "series": [{"x": item["label"], "y": item["weigh_mass_g"]} for item in table],
        },
        "interpretation_hints": [
            "Use the basis_elements field to see which elements were exactly balanced.",
            "O/H/C/N balance is often volatile or atmosphere-dependent in solid-state synthesis and should be checked against the actual heating program.",
            "This planner computes stoichiometry only; it does not validate phase stability, reaction pathway, or safety.",
        ],
    }
