"""Lightweight package-backed utilities for materials analysis."""

from __future__ import annotations

import csv
import io
import math
from typing import Any

from .errors import FormulaError, MaterialsDependencyError
from .formula_analysis import parse_formula
from .structure_analysis import _coerce_structure_text, _guess_structure_format, _load_periodic_structure


def _round(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number, digits)


def _require_mendeleev():
    try:
        from mendeleev import element
    except Exception as exc:  # pragma: no cover - dependency guard
        raise MaterialsDependencyError("mendeleev is required for element properties") from exc
    return element


def _require_matminer():
    try:
        from matminer.featurizers.composition import ElementProperty, Stoichiometry
        from pymatgen.core import Composition
    except Exception as exc:  # pragma: no cover - dependency guard
        raise MaterialsDependencyError("matminer and pymatgen are required for composition features") from exc
    return Composition, ElementProperty, Stoichiometry


def _require_pint():
    try:
        from pint import UnitRegistry
    except Exception as exc:  # pragma: no cover - dependency guard
        raise MaterialsDependencyError("pint is required for unit conversion") from exc
    return UnitRegistry


def _require_pybaselines():
    try:
        from pybaselines import Baseline
    except Exception as exc:  # pragma: no cover - dependency guard
        raise MaterialsDependencyError("pybaselines is required for spectrum baseline correction") from exc
    return Baseline


def _require_seekpath():
    try:
        import seekpath
    except Exception as exc:  # pragma: no cover - dependency guard
        raise MaterialsDependencyError("seekpath is required for high-symmetry k-path generation") from exc
    return seekpath


def _require_scipy_signal():
    try:
        from scipy.signal import find_peaks, peak_widths
    except Exception as exc:  # pragma: no cover - dependency guard
        raise MaterialsDependencyError("scipy is required for spectrum peak detection") from exc
    return find_peaks, peak_widths


def _require_lmfit():
    try:
        from lmfit.models import ConstantModel, GaussianModel, LorentzianModel, VoigtModel
    except Exception as exc:  # pragma: no cover - dependency guard
        raise MaterialsDependencyError("lmfit is required for spectrum peak fitting") from exc
    return ConstantModel, GaussianModel, LorentzianModel, VoigtModel


def _symbols_from_formula_or_list(formula: Any = None, elements: Any = None) -> list[str]:
    symbols: list[str] = []
    if formula:
        symbols.extend(parse_formula(formula).keys())
    if elements:
        if isinstance(elements, str):
            items = elements.replace(";", ",").split(",")
        elif isinstance(elements, (list, tuple, set)):
            items = list(elements)
        else:
            raise FormulaError("elements must be a string or list")
        symbols.extend(str(item or "").strip() for item in items)
    cleaned = sorted({symbol for symbol in symbols if symbol})
    if not cleaned:
        raise FormulaError("provide formula or elements")
    if len(cleaned) > 12:
        raise FormulaError("element property lookup is limited to 12 elements")
    return cleaned


def element_properties(formula: Any = None, elements: Any = None) -> dict[str, Any]:
    """Return tabular element properties from mendeleev."""

    element = _require_mendeleev()
    symbols = _symbols_from_formula_or_list(formula=formula, elements=elements)
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        try:
            item = element(symbol)
        except Exception as exc:
            raise FormulaError(f"unknown element symbol: {symbol}") from exc
        ionization_energy = None
        try:
            ionization_energy = item.ionenergies.get(1)
        except Exception:
            ionization_energy = None
        rows.append(
            {
                "symbol": item.symbol,
                "name": item.name,
                "atomic_number": item.atomic_number,
                "atomic_weight": _round(item.atomic_weight, 6),
                "period": item.period,
                "group": item.group_id,
                "block": item.block,
                "electronegativity_pauling": _round(item.en_pauling, 4),
                "covalent_radius_pyykko_pm": _round(item.covalent_radius_pyykko, 3),
                "atomic_radius_pm": _round(item.atomic_radius, 3),
                "electron_affinity_ev": _round(item.electron_affinity, 6),
                "first_ionization_energy_ev": _round(ionization_energy, 6),
            }
        )

    return {
        "success": True,
        "version": "1.0",
        "source": "mendeleev",
        "engine": "mendeleev",
        "query": {"formula": str(formula or "").strip(), "elements": symbols},
        "count": len(rows),
        "properties": rows,
        "data_quality": {
            "computed_from": "periodic_table_reference_data",
            "external_database_lookup": False,
            "experimental": False,
        },
        "limitations": [
            "Element properties are reference descriptors and do not determine phase stability, structure, or application fitness by themselves.",
        ],
    }


def _coerce_feature_limit(max_features: Any, feature_count: int) -> int:
    if max_features is None or str(max_features).strip() == "":
        return feature_count
    try:
        return max(1, min(int(max_features), min(feature_count, 200)))
    except (TypeError, ValueError) as exc:
        raise FormulaError("max_features must be an integer") from exc


def _composition_feature_vector(formula: Any) -> tuple[Any, dict[str, float | int | None]]:
    Composition, ElementProperty, Stoichiometry = _require_matminer()
    cleaned = str(formula or "").strip()
    if not cleaned:
        raise FormulaError("formula is required")
    if len(cleaned) > 200:
        raise FormulaError("formula is limited to 200 characters")
    try:
        composition = Composition(cleaned)
    except Exception as exc:
        raise FormulaError(f"invalid formula: {cleaned}") from exc

    featurizers = [Stoichiometry(), ElementProperty.from_preset("magpie")]
    features: dict[str, float | int | None] = {}
    for featurizer in featurizers:
        labels = featurizer.feature_labels()
        values = featurizer.featurize(composition)
        for label, value in zip(labels, values):
            if isinstance(value, int):
                features[label] = value
            else:
                features[label] = _round(value, 8)
    return composition, features


def composition_features(formula: Any, max_features: int | None = None) -> dict[str, Any]:
    """Compute composition descriptors with matminer."""

    cleaned = str(formula or "").strip()
    composition, features = _composition_feature_vector(cleaned)
    feature_limit = _coerce_feature_limit(max_features, len(features))

    selected_labels = [
        "0-norm",
        "2-norm",
        "MagpieData mean Number",
        "MagpieData range Number",
        "MagpieData mean AtomicWeight",
        "MagpieData mean Electronegativity",
        "MagpieData range Electronegativity",
        "MagpieData mean CovalentRadius",
        "MagpieData avg_dev CovalentRadius",
        "MagpieData mean MeltingT",
    ]
    highlighted = [
        {"name": label, "value": features.get(label)}
        for label in selected_labels
        if label in features
    ]

    limited_features = dict(list(features.items())[:feature_limit])
    is_truncated = len(limited_features) < len(features)
    return {
        "success": True,
        "version": "1.0",
        "source": "matminer.featurizers.composition",
        "engine": "matminer",
        "formula": cleaned,
        "reduced_formula": composition.reduced_formula,
        "feature_count": len(features),
        "returned_feature_count": len(limited_features),
        "truncated": is_truncated,
        "features": limited_features,
        "highlighted_features": highlighted,
        "data_quality": {
            "computed_from": "chemical_formula",
            "external_database_lookup": False,
            "experimental": False,
        },
        "limitations": [
            "Composition descriptors are model input features, not property predictions.",
            "Use validated models or database/experimental properties before making application claims.",
        ],
    }


def _coerce_formula_list(formulas: Any) -> list[str]:
    if isinstance(formulas, str):
        items = [
            item.strip()
            for item in formulas.replace(",", " ").replace(";", " ").split()
            if item.strip()
        ]
    elif isinstance(formulas, (list, tuple)):
        items = [str(item or "").strip() for item in formulas if str(item or "").strip()]
    else:
        raise FormulaError("formulas must be a non-empty list or whitespace-separated string")
    if not items:
        raise FormulaError("formulas must be a non-empty list")
    if len(items) > 50:
        raise FormulaError("batch composition features are limited to 50 formulas per request")
    return items


def _records_to_csv(columns: list[str], rows: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def batch_composition_features(
    formulas: Any,
    max_features: int | None = None,
    *,
    include_csv: bool = True,
) -> dict[str, Any]:
    """Compute a rectangular matminer feature table for up to 50 formulas."""

    formula_items = _coerce_formula_list(formulas)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    feature_columns: list[str] | None = None

    for index, formula in enumerate(formula_items):
        try:
            composition, features = _composition_feature_vector(formula)
            if feature_columns is None:
                feature_limit = _coerce_feature_limit(max_features, len(features))
                feature_columns = list(features.keys())[:feature_limit]
            row: dict[str, Any] = {
                "row_index": index,
                "formula": formula,
                "reduced_formula": composition.reduced_formula,
            }
            for column in feature_columns:
                row[column] = features.get(column)
            rows.append(row)
        except FormulaError as exc:
            errors.append({"row_index": index, "formula": formula, "error": str(exc)})

    if not rows:
        raise FormulaError("no valid formulas were available for composition feature calculation")

    feature_columns = feature_columns or []
    columns = ["row_index", "formula", "reduced_formula", *feature_columns]
    payload: dict[str, Any] = {
        "success": True,
        "version": "1.0",
        "source": "matminer.featurizers.composition",
        "engine": "matminer",
        "input_count": len(formula_items),
        "count": len(rows),
        "error_count": len(errors),
        "feature_count": len(feature_columns),
        "columns": columns,
        "feature_columns": feature_columns,
        "shape": {"rows": len(rows), "columns": len(columns)},
        "records": rows,
        "errors": errors,
        "ml_ready": len(errors) == 0,
        "table_format": "records_and_csv",
        "data_quality": {
            "computed_from": "chemical_formula",
            "external_database_lookup": False,
            "experimental": False,
            "rectangular_feature_matrix": True,
        },
        "limitations": [
            "Composition descriptors are model input features, not property predictions.",
            "Rows with invalid formulas are excluded from the feature matrix and listed under errors.",
            "Use validated models or database/experimental properties before making application claims.",
        ],
    }
    if include_csv:
        payload["csv"] = _records_to_csv(columns, rows)
    return payload


def convert_unit(
    value: Any,
    from_unit: Any,
    to_unit: Any,
    *,
    per_mole: bool = False,
) -> dict[str, Any]:
    """Convert scientific units with pint."""

    UnitRegistry = _require_pint()
    try:
        magnitude = float(value)
    except (TypeError, ValueError) as exc:
        raise FormulaError("value must be numeric") from exc
    source_unit = str(from_unit or "").strip()
    target_unit = str(to_unit or "").strip()
    if not source_unit or not target_unit:
        raise FormulaError("from_unit and to_unit are required")

    registry = UnitRegistry()
    try:
        quantity = magnitude * registry(source_unit)
        if per_mole:
            quantity = quantity * registry.avogadro_constant
        converted = quantity.to(target_unit)
    except Exception as exc:
        raise FormulaError(f"could not convert {source_unit} to {target_unit}: {exc}") from exc

    return {
        "success": True,
        "version": "1.0",
        "source": "pint.UnitRegistry",
        "engine": "pint",
        "input": {
            "value": magnitude,
            "unit": source_unit,
            "per_mole": bool(per_mole),
        },
        "output": {
            "value": _round(converted.magnitude, 10),
            "unit": str(converted.units),
            "formatted": f"{converted.magnitude:.10g} {converted.units}",
        },
        "data_quality": {
            "computed_from": "unit_registry_conversion",
            "external_database_lookup": False,
            "experimental": False,
        },
    }


def _parse_xy_text(xy_text: Any) -> tuple[list[float], list[float]]:
    rows: list[tuple[float, float]] = []
    for line in str(xy_text or "").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        parts = [item for item in cleaned.replace(",", " ").replace(";", " ").split() if item]
        if len(parts) < 2:
            continue
        try:
            rows.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    if not rows:
        raise FormulaError("xy_text must contain numeric x y rows")
    return [item[0] for item in rows], [item[1] for item in rows]


def _coerce_xy(x_values: Any = None, y_values: Any = None, xy_text: Any = None) -> tuple[list[float], list[float]]:
    if xy_text:
        return _parse_xy_text(xy_text)
    if not isinstance(x_values, list) or not isinstance(y_values, list):
        raise FormulaError("provide xy_text or x_values and y_values lists")
    if len(x_values) != len(y_values) or not x_values:
        raise FormulaError("x_values and y_values must be non-empty lists with equal length")
    try:
        x = [float(item) for item in x_values]
        y = [float(item) for item in y_values]
    except (TypeError, ValueError) as exc:
        raise FormulaError("x_values and y_values must be numeric") from exc
    return x, y


def correct_spectrum_baseline(
    *,
    x_values: Any = None,
    y_values: Any = None,
    xy_text: Any = None,
    method: str = "asls",
    lam: float = 100000.0,
    p: float = 0.01,
) -> dict[str, Any]:
    """Baseline-correct XRD/Raman/FTIR-like XY data with pybaselines."""

    Baseline = _require_pybaselines()
    x, y = _coerce_xy(x_values=x_values, y_values=y_values, xy_text=xy_text)
    if len(x) < 3:
        raise FormulaError("at least three XY points are required")
    if len(x) > 3000:
        raise FormulaError("baseline correction is limited to 3000 points on VPS deployments")

    method_name = str(method or "asls").strip().lower()
    baseline_runner = Baseline(x_data=x)
    if method_name == "asls":
        baseline, params = baseline_runner.asls(y, lam=float(lam), p=float(p))
    elif method_name == "airpls":
        baseline, params = baseline_runner.airpls(y, lam=float(lam))
    elif method_name == "modpoly":
        baseline, params = baseline_runner.modpoly(y, poly_order=2)
    else:
        raise FormulaError("method must be asls, airpls, or modpoly")

    corrected = [float(yi) - float(bi) for yi, bi in zip(y, baseline)]
    series = [
        {
            "x": _round(xi, 8),
            "raw": _round(yi, 8),
            "baseline": _round(bi, 8),
            "corrected": _round(ci, 8),
        }
        for xi, yi, bi, ci in zip(x, y, baseline, corrected)
    ]
    return {
        "success": True,
        "version": "1.0",
        "source": "pybaselines.Baseline",
        "engine": "pybaselines",
        "method": method_name,
        "point_count": len(series),
        "parameters": {
            "lam": float(lam),
            "p": float(p),
            "returned": sorted(str(key) for key in params.keys()),
        },
        "summary": {
            "raw_min": _round(min(y), 6),
            "raw_max": _round(max(y), 6),
            "corrected_min": _round(min(corrected), 6),
            "corrected_max": _round(max(corrected), 6),
        },
        "visualization": {
            "type": "xy_baseline_correction",
            "x_axis": "x",
            "y_axis": "intensity",
            "series": series[:1000],
            "truncated": len(series) > 1000,
        },
        "data_quality": {
            "computed_from": "uploaded_xy_data",
            "external_database_lookup": False,
            "experimental": True,
        },
        "limitations": [
            "Baseline correction depends on method and parameter choices; inspect corrected curves before quantitative interpretation.",
        ],
    }


def detect_spectrum_peaks(
    *,
    x_values: Any = None,
    y_values: Any = None,
    xy_text: Any = None,
    prominence: Any = None,
    height: Any = None,
    distance: Any = None,
    max_peaks: int = 50,
) -> dict[str, Any]:
    """Detect peaks in small uploaded XY spectra with scipy.signal."""

    find_peaks, peak_widths = _require_scipy_signal()
    x, y = _coerce_xy(x_values=x_values, y_values=y_values, xy_text=xy_text)
    if len(x) < 3:
        raise FormulaError("at least three XY points are required")
    if len(x) > 3000:
        raise FormulaError("peak detection is limited to 3000 points on VPS deployments")
    try:
        peak_limit = max(1, min(int(max_peaks or 50), 200))
    except (TypeError, ValueError) as exc:
        raise FormulaError("max_peaks must be an integer") from exc

    y_range = max(y) - min(y)
    auto_prominence = None
    if prominence is None or str(prominence).strip() == "":
        auto_prominence = max(abs(y_range) * 0.05, 1e-12)
        prominence_value: float | None = auto_prominence
    else:
        try:
            prominence_value = float(prominence)
        except (TypeError, ValueError) as exc:
            raise FormulaError("prominence must be numeric") from exc
    if height is None or str(height).strip() == "":
        height_value = None
    else:
        try:
            height_value = float(height)
        except (TypeError, ValueError) as exc:
            raise FormulaError("height must be numeric") from exc
    if distance is None or str(distance).strip() == "":
        distance_value = None
    else:
        try:
            distance_value = max(1, int(float(distance)))
        except (TypeError, ValueError) as exc:
            raise FormulaError("distance must be numeric") from exc

    indices, properties = find_peaks(
        y,
        prominence=prominence_value,
        height=height_value,
        distance=distance_value,
    )
    widths_result = peak_widths(y, indices, rel_height=0.5) if len(indices) else ([], [], [], [])

    peaks: list[dict[str, Any]] = []
    for rank, peak_index in enumerate(indices):
        left_ip = float(widths_result[2][rank]) if len(widths_result[2]) > rank else None
        right_ip = float(widths_result[3][rank]) if len(widths_result[3]) > rank else None
        width_points = float(widths_result[0][rank]) if len(widths_result[0]) > rank else None
        x_width = None
        if left_ip is not None and right_ip is not None and len(x) > 1:
            spacing = (max(x) - min(x)) / max(len(x) - 1, 1)
            x_width = width_points * spacing if width_points is not None else None
        peaks.append(
            {
                "index": int(peak_index),
                "x": _round(x[int(peak_index)], 8),
                "y": _round(y[int(peak_index)], 8),
                "prominence": _round(properties.get("prominences", [None] * len(indices))[rank], 8),
                "width_points": _round(width_points, 4),
                "width_x_units": _round(x_width, 8),
                "left_base_index": int(properties.get("left_bases", [peak_index] * len(indices))[rank]),
                "right_base_index": int(properties.get("right_bases", [peak_index] * len(indices))[rank]),
            }
        )

    peaks.sort(key=lambda item: float(item.get("prominence") or 0.0), reverse=True)
    returned = peaks[:peak_limit]
    returned.sort(key=lambda item: float(item.get("x") or 0.0))
    series = [
        {"x": _round(xi, 8), "y": _round(yi, 8)}
        for xi, yi in zip(x, y)
    ]
    return {
        "success": True,
        "version": "1.0",
        "source": "scipy.signal.find_peaks",
        "engine": "scipy",
        "point_count": len(x),
        "peak_count": len(peaks),
        "returned_peak_count": len(returned),
        "peaks": returned,
        "parameters": {
            "prominence": _round(prominence_value, 8),
            "auto_prominence": _round(auto_prominence, 8),
            "height": _round(height_value, 8),
            "distance": distance_value,
            "max_peaks": peak_limit,
        },
        "visualization": {
            "type": "xy_peak_detection",
            "x_axis": "x",
            "y_axis": "intensity",
            "series": series[:1000],
            "peaks": returned,
            "truncated": len(series) > 1000,
        },
        "data_quality": {
            "computed_from": "uploaded_xy_data",
            "external_database_lookup": False,
            "experimental": True,
        },
        "limitations": [
            "Peak detection depends on prominence, height, spacing, smoothing, and baseline choices.",
            "Use instrument calibration and domain-specific preprocessing before publication-grade quantification.",
        ],
    }


def fit_spectrum_peaks(
    *,
    x_values: Any = None,
    y_values: Any = None,
    xy_text: Any = None,
    peak_positions: Any = None,
    model: str = "gaussian",
    max_peaks: int = 5,
    prominence: Any = None,
) -> dict[str, Any]:
    """Fit Gaussian/Lorentzian/Voigt peak models to small XY spectra."""

    import numpy as np

    ConstantModel, GaussianModel, LorentzianModel, VoigtModel = _require_lmfit()
    find_peaks, peak_widths = _require_scipy_signal()
    x_raw, y_raw = _coerce_xy(x_values=x_values, y_values=y_values, xy_text=xy_text)
    if len(x_raw) < 7:
        raise FormulaError("at least seven XY points are required for peak fitting")
    if len(x_raw) > 3000:
        raise FormulaError("peak fitting is limited to 3000 points on VPS deployments")

    x = np.asarray(x_raw, dtype=float)
    y = np.asarray(y_raw, dtype=float)
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    try:
        peak_limit = max(1, min(int(max_peaks or 5), 10))
    except (TypeError, ValueError) as exc:
        raise FormulaError("max_peaks must be an integer") from exc

    model_name = str(model or "gaussian").strip().lower()
    if model_name == "gaussian":
        peak_model_class = GaussianModel
    elif model_name == "lorentzian":
        peak_model_class = LorentzianModel
    elif model_name == "voigt":
        peak_model_class = VoigtModel
    else:
        raise FormulaError("model must be gaussian, lorentzian, or voigt")

    if isinstance(peak_positions, list) and peak_positions:
        centers = [float(item) for item in peak_positions[:peak_limit]]
        peak_indices = [
            int(np.argmin(np.abs(x - center)))
            for center in centers
        ]
        widths = np.full(len(peak_indices), max((float(x.max()) - float(x.min())) / 40.0, 1e-6))
    else:
        y_range = float(y.max() - y.min())
        if prominence is None or str(prominence).strip() == "":
            prominence_value = max(abs(y_range) * 0.05, 1e-12)
        else:
            try:
                prominence_value = float(prominence)
            except (TypeError, ValueError) as exc:
                raise FormulaError("prominence must be numeric") from exc
        detected, properties = find_peaks(y, prominence=prominence_value)
        if len(detected) == 0:
            raise FormulaError("no peaks detected; provide peak_positions or lower prominence")
        prominences = properties.get("prominences", np.ones(len(detected)))
        ranked = sorted(
            range(len(detected)),
            key=lambda idx: float(prominences[idx]),
            reverse=True,
        )[:peak_limit]
        peak_indices = [int(detected[idx]) for idx in ranked]
        width_result = peak_widths(y, peak_indices, rel_height=0.5)
        spacing = float((x.max() - x.min()) / max(len(x) - 1, 1))
        widths = np.asarray(width_result[0], dtype=float) * spacing

    peak_indices = sorted(set(peak_indices), key=lambda idx: float(x[idx]))
    if not peak_indices:
        raise FormulaError("no usable peak positions were provided")

    composite = ConstantModel(prefix="bkg_")
    params = composite.make_params(c=float(np.percentile(y, 5)))
    x_min = float(x.min())
    x_max = float(x.max())
    for idx, peak_index in enumerate(peak_indices):
        prefix = f"p{idx}_"
        peak_model = peak_model_class(prefix=prefix)
        composite = composite + peak_model
        params.update(peak_model.make_params())
        center = float(x[peak_index])
        height = max(float(y[peak_index] - np.percentile(y, 5)), 1e-9)
        sigma = max(float(widths[min(idx, len(widths) - 1)]) / 2.355, (x_max - x_min) / 1000.0, 1e-9)
        params[f"{prefix}center"].set(value=center, min=x_min, max=x_max)
        if f"{prefix}sigma" in params:
            params[f"{prefix}sigma"].set(value=sigma, min=1e-9, max=max(x_max - x_min, 1e-9))
        if f"{prefix}amplitude" in params:
            params[f"{prefix}amplitude"].set(value=max(height * sigma * 2.5, 1e-9), min=0.0)

    try:
        result = composite.fit(y, params, x=x, nan_policy="omit")
    except Exception as exc:
        raise FormulaError(f"could not fit peaks: {exc}") from exc

    fitted_peaks: list[dict[str, Any]] = []
    for idx, _peak_index in enumerate(peak_indices):
        prefix = f"p{idx}_"
        center = result.params.get(f"{prefix}center")
        sigma = result.params.get(f"{prefix}sigma")
        amplitude = result.params.get(f"{prefix}amplitude")
        fwhm = result.params.get(f"{prefix}fwhm")
        height = result.params.get(f"{prefix}height")
        fitted_peaks.append(
            {
                "index": idx,
                "center": _round(center.value if center is not None else None, 8),
                "sigma": _round(sigma.value if sigma is not None else None, 8),
                "fwhm": _round(fwhm.value if fwhm is not None else None, 8),
                "height": _round(height.value if height is not None else None, 8),
                "area": _round(amplitude.value if amplitude is not None else None, 8),
            }
        )

    series = [
        {
            "x": _round(xi, 8),
            "y": _round(yi, 8),
            "fit": _round(fi, 8),
            "residual": _round(ri, 8),
        }
        for xi, yi, fi, ri in zip(x.tolist(), y.tolist(), result.best_fit.tolist(), result.residual.tolist())
    ]
    return {
        "success": True,
        "version": "1.0",
        "source": "lmfit.models",
        "engine": "lmfit",
        "model": model_name,
        "point_count": int(len(x)),
        "peak_count": len(fitted_peaks),
        "peaks": fitted_peaks,
        "fit_statistics": {
            "chisqr": _round(result.chisqr, 8),
            "redchi": _round(result.redchi, 8),
            "aic": _round(result.aic, 8),
            "bic": _round(result.bic, 8),
            "success": bool(result.success),
            "message": str(result.message),
        },
        "visualization": {
            "type": "xy_peak_fit",
            "x_axis": "x",
            "y_axis": "intensity",
            "series": series[:1000],
            "truncated": len(series) > 1000,
        },
        "data_quality": {
            "computed_from": "uploaded_xy_data",
            "external_database_lookup": False,
            "experimental": True,
        },
        "limitations": [
            "Peak fitting is sensitive to baseline, initial peak positions, overlap, and chosen line-shape model.",
            "Use calibrated instrument metadata and residual inspection before publication-grade quantitative interpretation.",
        ],
    }


def high_symmetry_kpath(
    structure_text: Any,
    file_format: str | None = "auto",
    symprec: float = 0.1,
) -> dict[str, Any]:
    """Generate a high-symmetry reciprocal-space path with seekpath."""

    seekpath = _require_seekpath()
    text = _coerce_structure_text(structure_text)
    fmt = _guess_structure_format(text, file_format)
    if fmt == "xyz":
        raise FormulaError("high-symmetry k-path requires a periodic CIF or POSCAR structure")
    structure = _load_periodic_structure(text, fmt)
    if len(structure) > 256:
        raise FormulaError("high-symmetry k-path is limited to 256 sites on VPS deployments")
    cell = (
        structure.lattice.matrix.tolist(),
        [site.frac_coords.tolist() for site in structure.sites],
        [int(site.specie.Z) for site in structure.sites],
    )
    try:
        path_data = seekpath.get_path(cell, symprec=float(symprec or 0.1))
    except Exception as exc:
        raise FormulaError(f"could not generate k-path: {exc}") from exc

    point_coords = {
        str(label): [_round(value, 8) for value in coords]
        for label, coords in path_data.get("point_coords", {}).items()
    }
    path = [[str(a), str(b)] for a, b in path_data.get("path", [])]
    return {
        "success": True,
        "version": "1.0",
        "source": "seekpath.get_path",
        "engine": "seekpath",
        "format": fmt,
        "formula": structure.composition.reduced_formula,
        "bravais_lattice": path_data.get("bravais_lattice"),
        "bravais_lattice_extended": path_data.get("bravais_lattice_extended"),
        "spacegroup_number": path_data.get("spacegroup_number"),
        "spacegroup_international": path_data.get("spacegroup_international"),
        "has_inversion_symmetry": path_data.get("has_inversion_symmetry"),
        "point_coords": point_coords,
        "path": path,
        "segment_count": len(path),
        "data_quality": {
            "computed_from": f"uploaded_{fmt}",
            "external_database_lookup": False,
            "experimental": False,
        },
        "limitations": [
            "The k-path is a standardized reciprocal-space path for calculations; it is not an electronic band-structure result.",
        ],
    }
