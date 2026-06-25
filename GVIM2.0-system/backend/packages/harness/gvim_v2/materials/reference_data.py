"""Reference-data backed lightweight materials and chemistry lookups."""

from __future__ import annotations

import math
from typing import Any
from urllib.parse import quote

from .advanced_analysis import _symbols_from_formula_or_list
from .errors import FormulaError, MaterialsDependencyError


PUBCHEM_PROPERTIES = [
    "MolecularFormula",
    "MolecularWeight",
    "CanonicalSMILES",
    "IsomericSMILES",
    "InChI",
    "InChIKey",
    "IUPACName",
    "XLogP",
    "TPSA",
    "ExactMass",
    "Charge",
]


def _round(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number, digits)


def _require_requests():
    try:
        import requests
    except Exception as exc:  # pragma: no cover - dependency guard
        raise MaterialsDependencyError("requests is required for external reference API lookups") from exc
    return requests


def _require_xraydb():
    try:
        import xraydb
    except Exception as exc:  # pragma: no cover - dependency guard
        raise MaterialsDependencyError("xraydb is required for X-ray reference data") from exc
    return xraydb


def _require_periodictable():
    try:
        import periodictable
    except Exception as exc:  # pragma: no cover - dependency guard
        raise MaterialsDependencyError("periodictable is required for scattering reference data") from exc
    return periodictable


def _request_json(url: str, *, params: dict[str, Any] | None = None, timeout: float = 12.0) -> tuple[int, Any]:
    requests = _require_requests()
    try:
        response = requests.get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise MaterialsDependencyError(f"reference API request failed: {exc}") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise MaterialsDependencyError(
            f"reference API returned non-JSON response with status {response.status_code}"
        ) from exc
    return response.status_code, payload


def _coerce_limit(value: Any, *, default: int = 5, maximum: int = 10) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(limit, maximum))


def resolve_pubchem_compound(
    query: Any,
    *,
    namespace: str = "name",
    limit: int = 5,
) -> dict[str, Any]:
    """Resolve a compound through PubChem PUG-REST and return factual records."""

    cleaned = str(query or "").strip()
    if not cleaned:
        raise FormulaError("query is required")
    namespace_clean = str(namespace or "name").strip().lower()
    allowed = {"name", "smiles", "inchi", "inchikey", "cid"}
    if namespace_clean not in allowed:
        raise FormulaError("namespace must be name, smiles, inchi, inchikey, or cid")
    result_limit = _coerce_limit(limit, default=5, maximum=10)

    encoded_query = quote(cleaned, safe="")
    properties = ",".join(PUBCHEM_PROPERTIES)
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
        f"{namespace_clean}/{encoded_query}/property/{properties}/JSON"
    )
    status_code, payload = _request_json(url)
    if status_code == 404:
        rows: list[dict[str, Any]] = []
    elif status_code >= 400:
        fault = payload.get("Fault", {}) if isinstance(payload, dict) else {}
        message = fault.get("Message") if isinstance(fault, dict) else None
        raise MaterialsDependencyError(f"PubChem lookup failed: {message or status_code}")
    else:
        table = payload.get("PropertyTable", {}) if isinstance(payload, dict) else {}
        raw_rows = table.get("Properties", []) if isinstance(table, dict) else []
        if not isinstance(raw_rows, list):
            raw_rows = []
        rows = []
        for item in raw_rows[:result_limit]:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "cid": item.get("CID"),
                    "molecular_formula": item.get("MolecularFormula"),
                    "molecular_weight": _round(item.get("MolecularWeight"), 6),
                    "exact_mass": _round(item.get("ExactMass"), 6),
                    "canonical_smiles": item.get("CanonicalSMILES"),
                    "isomeric_smiles": item.get("IsomericSMILES"),
                    "inchi": item.get("InChI"),
                    "inchikey": item.get("InChIKey"),
                    "iupac_name": item.get("IUPACName"),
                    "xlogp": _round(item.get("XLogP"), 6),
                    "tpsa": _round(item.get("TPSA"), 6),
                    "charge": item.get("Charge"),
                }
            )

    return {
        "success": True,
        "version": "1.0",
        "source": "PubChem PUG-REST",
        "engine": "requests",
        "query": {
            "query": cleaned,
            "namespace": namespace_clean,
            "limit": result_limit,
        },
        "count": len(rows),
        "compounds": rows,
        "data_quality": {
            "computed_from": "pubchem_compound_database",
            "external_database_lookup": True,
            "experimental": False,
        },
        "limitations": [
            "PubChem records are compound identifiers and descriptors; they are not evidence of material phase stability or synthesis feasibility.",
            "For salts, mixtures, hydrates, or ambiguous names, verify the returned CID/InChIKey before using descriptors.",
        ],
    }


def search_optimade_structures(
    *,
    formula: Any = None,
    elements: Any = None,
    provider_url: Any = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Search an OPTIMADE-compatible structures endpoint with explicit filters."""

    formula_clean = str(formula or "").strip()
    symbols: list[str] = []
    if elements:
        symbols = _symbols_from_formula_or_list(elements=elements)
    elif formula_clean:
        symbols = _symbols_from_formula_or_list(formula=formula_clean)
    if not formula_clean and not symbols:
        raise FormulaError("provide formula or elements")

    result_limit = _coerce_limit(limit, default=5, maximum=10)
    endpoint = str(provider_url or "https://optimade.materialsproject.org/v1/structures").strip()
    if not endpoint.startswith(("http://", "https://")):
        raise FormulaError("provider_url must be an http or https URL")

    filters: list[str] = []
    if formula_clean:
        filters.append(f'chemical_formula_reduced="{formula_clean}"')
    if symbols:
        filters.append("elements HAS ALL " + ", ".join(f'"{symbol}"' for symbol in symbols))
    optimade_filter = " AND ".join(filters)
    status_code, payload = _request_json(
        endpoint,
        params={
            "filter": optimade_filter,
            "page_limit": result_limit,
        },
    )
    if status_code >= 400:
        errors = payload.get("errors", []) if isinstance(payload, dict) else []
        message = None
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            message = errors[0].get("detail") or errors[0].get("title")
        raise MaterialsDependencyError(f"OPTIMADE lookup failed: {message or status_code}")

    raw_rows = payload.get("data", []) if isinstance(payload, dict) else []
    if not isinstance(raw_rows, list):
        raw_rows = []
    rows: list[dict[str, Any]] = []
    for item in raw_rows[:result_limit]:
        if not isinstance(item, dict):
            continue
        attributes = item.get("attributes", {})
        attributes = attributes if isinstance(attributes, dict) else {}
        rows.append(
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "chemical_formula_reduced": attributes.get("chemical_formula_reduced"),
                "chemical_formula_descriptive": attributes.get("chemical_formula_descriptive"),
                "elements": attributes.get("elements"),
                "nelements": attributes.get("nelements"),
                "nsites": attributes.get("nsites"),
                "immutable_id": attributes.get("immutable_id"),
                "last_modified": attributes.get("last_modified"),
                "structure_features": attributes.get("structure_features"),
            }
        )

    return {
        "success": True,
        "version": "1.0",
        "source": "OPTIMADE structures API",
        "engine": "requests",
        "query": {
            "formula": formula_clean or None,
            "elements": symbols,
            "provider_url": endpoint,
            "filter": optimade_filter,
            "limit": result_limit,
        },
        "count": len(rows),
        "structures": rows,
        "data_quality": {
            "computed_from": "optimade_provider_database",
            "external_database_lookup": True,
            "experimental": False,
        },
        "limitations": [
            "OPTIMADE search confirms provider records and metadata only; it is not a replacement for phase stability, property, or provenance review.",
            "Returned fields depend on the selected provider and may be incomplete.",
        ],
    }


def xray_reference_data(
    *,
    formula: Any = None,
    elements: Any = None,
    edge: str = "K",
    max_lines: int = 8,
) -> dict[str, Any]:
    """Return X-ray absorption edge and emission-line reference data."""

    xraydb = _require_xraydb()
    symbols = _symbols_from_formula_or_list(formula=formula, elements=elements)
    edge_name = str(edge or "K").strip()
    line_limit = _coerce_limit(max_lines, default=8, maximum=20)
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        atomic_number = xraydb.atomic_number(symbol)
        if not atomic_number:
            raise FormulaError(f"unknown element symbol: {symbol}")
        try:
            edge_data = xraydb.xray_edge(symbol, edge_name)
        except Exception as exc:
            raise FormulaError(f"could not read {symbol} {edge_name} edge: {exc}") from exc
        raw_lines = xraydb.xray_lines(symbol, initial_level=edge_name)
        if isinstance(raw_lines, dict):
            line_items = raw_lines.items()
        else:
            line_items = []
        lines = []
        for name, line in list(line_items)[:line_limit]:
            lines.append(
                {
                    "line": str(name),
                    "energy_ev": _round(getattr(line, "energy", None), 4),
                    "intensity": _round(getattr(line, "intensity", None), 8),
                    "initial_level": getattr(line, "initial_level", None),
                    "final_level": getattr(line, "final_level", None),
                }
            )
        rows.append(
            {
                "symbol": symbol,
                "atomic_number": int(atomic_number),
                "edge": edge_name,
                "edge_energy_ev": _round(getattr(edge_data, "energy", None), 4),
                "fluorescence_yield": _round(getattr(edge_data, "fyield", None), 8),
                "jump_ratio": _round(getattr(edge_data, "jump_ratio", None), 8),
                "emission_lines": lines,
            }
        )

    return {
        "success": True,
        "version": "1.0",
        "source": "xraydb",
        "engine": "xraydb",
        "query": {
            "formula": str(formula or "").strip() or None,
            "elements": symbols,
            "edge": edge_name,
            "max_lines": line_limit,
        },
        "count": len(rows),
        "references": rows,
        "data_quality": {
            "computed_from": "xray_reference_database",
            "external_database_lookup": False,
            "experimental": False,
        },
        "limitations": [
            "X-ray reference energies support spectroscopy setup and peak labeling; they do not identify a phase without measured spectra and contextual analysis.",
        ],
    }


def scattering_reference_data(
    *,
    formula: Any = None,
    elements: Any = None,
) -> dict[str, Any]:
    """Return neutron scattering lengths/cross sections and basic element rows."""

    periodictable = _require_periodictable()
    symbols = _symbols_from_formula_or_list(formula=formula, elements=elements)
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        try:
            element = getattr(periodictable, symbol)
        except AttributeError as exc:
            raise FormulaError(f"unknown element symbol: {symbol}") from exc
        neutron = getattr(element, "neutron", None)
        rows.append(
            {
                "symbol": symbol,
                "name": getattr(element, "name", None),
                "atomic_number": getattr(element, "number", None),
                "atomic_mass": _round(getattr(element, "mass", None), 6),
                "density_g_cm3": _round(getattr(element, "density", None), 6),
                "neutron_coherent_scattering_length_fm": _round(getattr(neutron, "b_c", None), 6),
                "neutron_coherent_cross_section_b": _round(getattr(neutron, "coherent", None), 6),
                "neutron_incoherent_cross_section_b": _round(getattr(neutron, "incoherent", None), 6),
                "neutron_absorption_cross_section_b": _round(getattr(neutron, "absorption", None), 6),
            }
        )

    return {
        "success": True,
        "version": "1.0",
        "source": "periodictable",
        "engine": "periodictable",
        "query": {
            "formula": str(formula or "").strip() or None,
            "elements": symbols,
        },
        "count": len(rows),
        "references": rows,
        "data_quality": {
            "computed_from": "periodic_table_scattering_reference_data",
            "external_database_lookup": False,
            "experimental": False,
        },
        "limitations": [
            "Scattering rows are element/isotope reference data and are not a simulated diffraction pattern.",
            "Natural-abundance values may be insufficient for isotope-enriched samples.",
        ],
    }
