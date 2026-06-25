"""Materials Project backed lookup utilities."""

from __future__ import annotations

import os
from typing import Any

from .errors import FormulaError, MaterialsDependencyError


SUMMARY_FIELDS = [
    "material_id",
    "formula_pretty",
    "chemsys",
    "elements",
    "band_gap",
    "is_gap_direct",
    "is_metal",
    "energy_above_hull",
    "formation_energy_per_atom",
    "is_stable",
    "density",
    "volume",
    "nsites",
    "symmetry",
]

THERMO_FIELDS = [
    "material_id",
    "thermo_id",
    "thermo_type",
    "formation_energy_per_atom",
    "energy_above_hull",
    "is_stable",
    "energy_per_atom",
    "equilibrium_reaction_energy_per_atom",
]

ELECTRONIC_FIELDS = [
    "material_id",
    "band_gap",
    "is_gap_direct",
    "is_metal",
    "efermi",
    "magnetic_ordering",
]

DIELECTRIC_FIELDS = [
    "material_id",
    "e_total",
    "e_ionic",
    "e_electronic",
    "n",
]

ELASTICITY_FIELDS = [
    "material_id",
    "elastic_tensor",
    "elastic_tensor_original",
    "compliance_tensor",
    "bulk_modulus",
    "shear_modulus",
    "universal_anisotropy",
    "homogeneous_poisson",
    "elastic_anisotropy",
    "g_voigt",
    "g_reuss",
    "g_vrh",
    "k_voigt",
    "k_reuss",
    "k_vrh",
    "poisson_ratio",
    "warnings",
]


def _get_api_key() -> str:
    api_key = (
        os.getenv("MP_API_KEY")
        or os.getenv("MATERIALS_PROJECT_API_KEY")
        or ""
    ).strip()
    if not api_key:
        raise MaterialsDependencyError(
            "MP_API_KEY is required for Materials Project lookup"
        )
    return api_key


def _require_mprester():
    try:
        from mp_api.client import MPRester
    except Exception as exc:  # pragma: no cover - dependency guard
        raise MaterialsDependencyError(
            "mp-api is required for Materials Project lookup"
        ) from exc
    return MPRester


def _string_list(value: Any, *, field: str, limit: int = 20) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [item.strip() for item in value.replace(";", ",").split(",")]
    elif isinstance(value, (list, tuple, set)):
        items = [str(item or "").strip() for item in value]
    else:
        raise FormulaError(f"{field} must be a string or list")
    cleaned = [item for item in items if item]
    if len(cleaned) > limit:
        raise FormulaError(f"{field} is limited to {limit} items")
    return cleaned


def _range_tuple(value: Any, *, field: str) -> tuple[float, float] | None:
    if value is None or value == "":
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise FormulaError(f"{field} must be [min, max]")
    try:
        low = float(value[0])
        high = float(value[1])
    except (TypeError, ValueError) as exc:
        raise FormulaError(f"{field} must contain numbers") from exc
    if low > high:
        raise FormulaError(f"{field} min must be <= max")
    return (low, high)


def _as_plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return _as_plain(value.model_dump())
    if isinstance(value, dict):
        return {str(key): _as_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_as_plain(item) for item in value]
    return str(value)


def _doc_payload(doc: Any) -> dict[str, Any]:
    data = doc.model_dump() if hasattr(doc, "model_dump") else dict(doc)

    def get(name: str) -> Any:
        return getattr(doc, name, data.get(name))

    material_id = get("material_id")
    symmetry = _as_plain(get("symmetry"))
    elements = [str(item) for item in (get("elements") or [])]

    return {
        "material_id": str(material_id) if material_id is not None else "",
        "formula_pretty": get("formula_pretty"),
        "chemical_system": get("chemsys"),
        "elements": elements,
        "band_gap_ev": get("band_gap"),
        "is_gap_direct": get("is_gap_direct"),
        "is_metal": get("is_metal"),
        "energy_above_hull_ev_atom": get("energy_above_hull"),
        "formation_energy_ev_atom": get("formation_energy_per_atom"),
        "is_stable": get("is_stable"),
        "density_g_cm3": get("density"),
        "volume_angstrom3": get("volume"),
        "site_count": get("nsites"),
        "symmetry": {
            "crystal_system": symmetry.get("crystal_system")
            if isinstance(symmetry, dict)
            else None,
            "symbol": symmetry.get("symbol") if isinstance(symmetry, dict) else None,
            "number": symmetry.get("number") if isinstance(symmetry, dict) else None,
            "point_group": symmetry.get("point_group")
            if isinstance(symmetry, dict)
            else None,
        },
    }


def _safe_number(value: Any) -> float | int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_call(obj: Any, method_name: str, *args: Any, **kwargs: Any) -> Any:
    method = getattr(obj, method_name, None)
    if not callable(method):
        return None
    try:
        return method(*args, **kwargs)
    except Exception:
        return None


def _sequence_values(value: Any, *, limit: int | None = None) -> list[Any]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, dict):
        values = list(value.values())
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        return []
    if limit is not None:
        values = values[:limit]
    return [_as_plain(item) for item in values]


def _numeric_sequence(value: Any) -> list[float]:
    numbers: list[float] = []
    for item in _sequence_values(value):
        number = _safe_number(item)
        if number is not None:
            numbers.append(float(number))
    return numbers


def _shape(value: Any) -> list[int]:
    shape = getattr(value, "shape", None)
    if shape is not None:
        try:
            return [int(item) for item in shape]
        except (TypeError, ValueError):
            return []
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], (list, tuple)):
            return [len(value), len(value[0])]
        return [len(value)]
    return []


def _downsample_xy(
    x_values: list[float],
    y_values: list[float],
    *,
    limit: int = 160,
) -> list[dict[str, float]]:
    if not x_values or not y_values:
        return []
    count = min(len(x_values), len(y_values))
    if count <= 0:
        return []
    step = max(1, count // limit)
    series = [
        {"x": round(float(x_values[index]), 6), "y": round(float(y_values[index]), 6)}
        for index in range(0, count, step)
    ]
    return series[:limit]


def _rank_profile_candidate(candidate: dict[str, Any]) -> tuple[int, float, str]:
    hull = _safe_number(candidate.get("energy_above_hull_ev_atom"))
    return (
        0 if candidate.get("is_stable") is True else 1,
        float(hull) if hull is not None else float("inf"),
        str(candidate.get("material_id") or ""),
    )


def _candidate_selection_payload(
    *,
    candidates: list[dict[str, Any]],
    selected: dict[str, Any],
    strategy: str,
    attempted_stable_filter: bool,
) -> dict[str, Any]:
    preview = []
    for item in sorted(candidates, key=_rank_profile_candidate)[:5]:
        symmetry = item.get("symmetry") if isinstance(item.get("symmetry"), dict) else {}
        preview.append(
            {
                "material_id": item.get("material_id"),
                "formula_pretty": item.get("formula_pretty"),
                "is_stable": item.get("is_stable"),
                "energy_above_hull_ev_atom": item.get("energy_above_hull_ev_atom"),
                "formation_energy_ev_atom": item.get("formation_energy_ev_atom"),
                "band_gap_ev": item.get("band_gap_ev"),
                "symmetry_symbol": symmetry.get("symbol"),
            }
        )
    return {
        "strategy": strategy,
        "attempted_stable_filter": attempted_stable_filter,
        "candidate_count": len(candidates),
        "selected_material_id": selected.get("material_id"),
        "selected_reason": (
            "material_id exact match"
            if strategy == "material_id_exact"
            else "stable entry preferred, then lowest energy_above_hull"
            if strategy == "stable_preferred_lowest_hull"
            else "no stable entry returned; selected lowest energy_above_hull among returned candidates"
        ),
        "candidates_considered": preview,
    }


def _build_summary_params(
    *,
    formula: Any = None,
    elements: Any = None,
    material_ids: Any = None,
    chemical_system: Any = None,
    is_stable: bool | None = None,
    band_gap: Any = None,
    energy_above_hull: Any = None,
    limit: Any = 10,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    formula_items = _string_list(formula, field="formula", limit=20)
    element_items = _string_list(elements, field="elements", limit=10)
    id_items = _string_list(material_ids, field="material_ids", limit=20)
    chemsys_items = _string_list(chemical_system, field="chemical_system", limit=20)
    try:
        result_limit = max(1, min(int(limit or 10), 25))
    except (TypeError, ValueError) as exc:
        raise FormulaError("limit must be an integer") from exc

    if not any([formula_items, element_items, id_items, chemsys_items]):
        raise FormulaError(
            "provide formula, elements, material_ids, or chemical_system"
        )

    params: dict[str, Any] = {
        "fields": SUMMARY_FIELDS,
        "num_chunks": 1,
        "chunk_size": result_limit,
    }
    if formula_items:
        params["formula"] = formula_items if len(formula_items) > 1 else formula_items[0]
    if element_items:
        params["elements"] = element_items
    if id_items:
        params["material_ids"] = id_items if len(id_items) > 1 else id_items[0]
    if chemsys_items:
        params["chemsys"] = chemsys_items if len(chemsys_items) > 1 else chemsys_items[0]
    if is_stable is not None:
        params["is_stable"] = bool(is_stable)
    band_gap_range = _range_tuple(band_gap, field="band_gap")
    if band_gap_range is not None:
        params["band_gap"] = band_gap_range
    hull_range = _range_tuple(energy_above_hull, field="energy_above_hull")
    if hull_range is not None:
        params["energy_above_hull"] = hull_range

    query = {
        "formula": formula_items,
        "elements": element_items,
        "material_ids": id_items,
        "chemical_system": chemsys_items,
        "is_stable": is_stable,
        "band_gap": list(band_gap_range) if band_gap_range is not None else None,
        "energy_above_hull": list(hull_range) if hull_range is not None else None,
        "limit": result_limit,
    }
    return params, query, result_limit


def _doc_subset(doc: Any, fields: list[str]) -> dict[str, Any]:
    data = doc.model_dump() if hasattr(doc, "model_dump") else {}
    payload: dict[str, Any] = {}
    for field in fields:
        value = getattr(doc, field, data.get(field))
        if value is not None:
            payload[field] = _as_plain(value)
    return payload


def _search_optional_rester(
    rester: Any,
    *,
    material_id: str,
    fields: list[str],
    max_records: int = 3,
) -> dict[str, Any]:
    try:
        docs = rester.search(
            material_ids=[material_id],
            fields=fields,
            num_chunks=1,
            chunk_size=max_records,
        )
        records = [_doc_subset(doc, fields) for doc in list(docs)[:max_records]]
        return {
            "available": bool(records),
            "record_count": len(records),
            "records": records,
        }
    except Exception as exc:
        first_error = str(exc)
        try:
            docs = rester.search(
                material_ids=[material_id],
                all_fields=True,
                num_chunks=1,
                chunk_size=max_records,
            )
            records = [_doc_subset(doc, fields) for doc in list(docs)[:max_records]]
            return {
                "available": bool(records),
                "record_count": len(records),
                "records": records,
                "field_retry": True,
                "field_error": first_error,
            }
        except Exception as retry_exc:
            return {
                "available": False,
                "record_count": 0,
                "records": [],
                "error": first_error or str(retry_exc),
            }


def _structure_payload(structure: Any) -> dict[str, Any]:
    composition = getattr(structure, "composition", None)
    lattice = getattr(structure, "lattice", None)
    lattice_payload = None
    if lattice is not None:
        lattice_payload = {
            "a": _safe_number(getattr(lattice, "a", None)),
            "b": _safe_number(getattr(lattice, "b", None)),
            "c": _safe_number(getattr(lattice, "c", None)),
            "alpha": _safe_number(getattr(lattice, "alpha", None)),
            "beta": _safe_number(getattr(lattice, "beta", None)),
            "gamma": _safe_number(getattr(lattice, "gamma", None)),
            "volume": _safe_number(getattr(lattice, "volume", None)),
        }
    return {
        "available": True,
        "formula": getattr(composition, "formula", None),
        "reduced_formula": getattr(composition, "reduced_formula", None),
        "site_count": len(structure) if hasattr(structure, "__len__") else None,
        "density_g_cm3": _safe_number(getattr(structure, "density", None)),
        "lattice": lattice_payload,
    }


def _select_material_profile_summary(
    mpr: Any,
    *,
    formula: Any = None,
    material_id: Any = None,
    chemical_system: Any = None,
) -> dict[str, Any]:
    if material_id:
        params, query, _result_limit = _build_summary_params(
            material_ids=material_id,
            limit=1,
        )
        docs = mpr.materials.summary.search(**params)
        summary_results = [_doc_payload(doc) for doc in list(docs)[:1]]
        selection_strategy = "material_id_exact"
        attempted_stable_filter = False
    else:
        stable_params, query, result_limit = _build_summary_params(
            formula=formula,
            chemical_system=chemical_system,
            is_stable=True,
            limit=25,
        )
        stable_docs = mpr.materials.summary.search(**stable_params)
        stable_results = [_doc_payload(doc) for doc in list(stable_docs)[:result_limit]]
        attempted_stable_filter = True
        if stable_results:
            summary_results = stable_results
            selection_strategy = "stable_preferred_lowest_hull"
        else:
            params, query, result_limit = _build_summary_params(
                formula=formula,
                chemical_system=chemical_system,
                limit=25,
            )
            docs = mpr.materials.summary.search(**params)
            summary_results = [_doc_payload(doc) for doc in list(docs)[:result_limit]]
            selection_strategy = "lowest_hull_fallback"

    if not summary_results:
        return {
            "found": False,
            "query": query,
            "summary_results": [],
            "summary": None,
            "selected_material_id": None,
            "selection": None,
        }

    summary = sorted(summary_results, key=_rank_profile_candidate)[0]
    selected_material_id = str(summary["material_id"])
    selection = _candidate_selection_payload(
        candidates=summary_results,
        selected=summary,
        strategy=selection_strategy,
        attempted_stable_filter=attempted_stable_filter,
    )
    return {
        "found": True,
        "query": query,
        "summary_results": summary_results,
        "summary": summary,
        "selected_material_id": selected_material_id,
        "selection": selection,
    }


def search_materials_project(
    *,
    formula: Any = None,
    elements: Any = None,
    material_ids: Any = None,
    chemical_system: Any = None,
    is_stable: bool | None = None,
    band_gap: Any = None,
    energy_above_hull: Any = None,
    limit: Any = 10,
) -> dict[str, Any]:
    """Search Materials Project summary data with the official mp-api client."""

    params, query, result_limit = _build_summary_params(
        formula=formula,
        elements=elements,
        material_ids=material_ids,
        chemical_system=chemical_system,
        is_stable=is_stable,
        band_gap=band_gap,
        energy_above_hull=energy_above_hull,
        limit=limit,
    )

    MPRester = _require_mprester()
    with MPRester(_get_api_key(), mute_progress_bars=True) as mpr:
        docs = mpr.materials.summary.search(**params)

    results = [_doc_payload(doc) for doc in docs[:result_limit]]
    return {
        "success": True,
        "version": "1.0",
        "source": "Materials Project",
        "engine": "mp-api",
        "query": query,
        "count": len(results),
        "results": results,
        "data_quality": {
            "computed_from": "materials_project_summary_database",
            "external_database_lookup": True,
            "experimental": False,
        },
        "limitations": [
            "Materials Project values are computed database results and can change with database releases.",
            "Formation energy, band gap, and stability values are not a substitute for experimental validation.",
        ],
    }


def materials_project_profile(
    *,
    formula: Any = None,
    material_id: Any = None,
    chemical_system: Any = None,
    include_thermo: bool = True,
    include_electronic: bool = True,
    include_dielectric: bool = True,
    include_structure: bool = True,
) -> dict[str, Any]:
    """Build a compact Materials Project evidence profile for one material."""

    MPRester = _require_mprester()
    with MPRester(_get_api_key(), mute_progress_bars=True) as mpr:
        selection_payload = _select_material_profile_summary(
            mpr,
            formula=formula,
            material_id=material_id,
            chemical_system=chemical_system,
        )
        query = selection_payload["query"]
        if not selection_payload["found"]:
            return {
                "success": True,
                "version": "1.0",
                "source": "Materials Project",
                "engine": "mp-api",
                "query": query,
                "profile_status": "not_found",
                "count": 0,
                "profile": None,
                "evidence": {},
                "data_quality": {
                    "computed_from": "materials_project_database",
                    "external_database_lookup": True,
                    "experimental": False,
                },
                "limitations": [
                    "No Materials Project record matched the query.",
                    "Absence from this lookup is not evidence that the material cannot exist.",
                ],
            }

        summary = selection_payload["summary"]
        selected_material_id = str(selection_payload["selected_material_id"])
        selection = selection_payload["selection"]
        evidence: dict[str, Any] = {}

        if include_structure:
            try:
                structure = mpr.materials.get_structure_by_material_id(selected_material_id)
                evidence["structure"] = _structure_payload(structure)
            except Exception as exc:
                evidence["structure"] = {"available": False, "error": str(exc)}

        if include_thermo:
            evidence["thermo"] = _search_optional_rester(
                mpr.materials.thermo,
                material_id=selected_material_id,
                fields=THERMO_FIELDS,
            )

        if include_electronic:
            evidence["electronic_structure"] = _search_optional_rester(
                mpr.materials.electronic_structure,
                material_id=selected_material_id,
                fields=ELECTRONIC_FIELDS,
            )

        if include_dielectric:
            evidence["dielectric"] = _search_optional_rester(
                mpr.materials.dielectric,
                material_id=selected_material_id,
                fields=DIELECTRIC_FIELDS,
            )

    return {
        "success": True,
        "version": "1.0",
        "source": "Materials Project",
        "engine": "mp-api",
        "query": query,
        "profile_status": "ready",
        "count": 1,
        "material_id": selected_material_id,
        "profile": summary,
        "selection": selection,
        "evidence": evidence,
        "data_quality": {
            "computed_from": "materials_project_database",
            "external_database_lookup": True,
            "experimental": False,
        },
        "limitations": [
            "Materials Project values are computed database results and can change with database releases.",
            "Thermodynamic, electronic, dielectric, and structure fields are evidence records, not experimental validation.",
            "Unavailable evidence sections indicate no returned record or an upstream API error; no substitute values are fabricated.",
        ],
    }


def _band_edge_payload(edge: Any) -> dict[str, Any] | None:
    if not isinstance(edge, dict):
        return None
    payload: dict[str, Any] = {}
    for key in ("energy", "band_index", "kpoint_index", "projections"):
        if key in edge:
            payload[key] = _as_plain(edge.get(key))
    kpoint = edge.get("kpoint")
    if kpoint is not None:
        payload["kpoint"] = {
            "label": getattr(kpoint, "label", None),
            "frac_coords": _sequence_values(getattr(kpoint, "frac_coords", None), limit=3),
        }
    return payload or None


def _band_structure_payload(band_structure: Any) -> dict[str, Any]:
    bands = getattr(band_structure, "bands", {}) or {}
    spin_channels: list[str] = []
    band_shape: list[int] = []
    for spin, values in bands.items() if isinstance(bands, dict) else []:
        spin_channels.append(str(spin).split(".")[-1])
        if not band_shape:
            band_shape = _shape(values)

    labels_dict = getattr(band_structure, "labels_dict", {}) or {}
    labels = sorted(str(label) for label in labels_dict.keys())[:40] if isinstance(labels_dict, dict) else []
    branches = _sequence_values(getattr(band_structure, "branches", None), limit=40)
    band_gap = _as_plain(_safe_call(band_structure, "get_band_gap"))
    cbm = _band_edge_payload(_safe_call(band_structure, "get_cbm"))
    vbm = _band_edge_payload(_safe_call(band_structure, "get_vbm"))
    kpoints = getattr(band_structure, "kpoints", None)
    kpoint_count = len(kpoints) if isinstance(kpoints, (list, tuple)) else None

    return {
        "available": True,
        "object": type(band_structure).__name__,
        "efermi_ev": _safe_number(getattr(band_structure, "efermi", None)),
        "is_metal": _safe_call(band_structure, "is_metal"),
        "band_gap": band_gap,
        "cbm": cbm,
        "vbm": vbm,
        "spin_channels": spin_channels,
        "band_shape": band_shape,
        "band_count": band_shape[0] if band_shape else None,
        "kpoint_count": kpoint_count if kpoint_count is not None else (band_shape[1] if len(band_shape) > 1 else None),
        "branch_count": len(branches),
        "branches": branches,
        "labels": labels,
        "data_quality": {
            "computed_from": "materials_project_line_mode_nscf_band_structure",
            "external_database_lookup": True,
            "experimental": False,
        },
        "limitations": [
            "Band structures are computed DFT/Kohn-Sham data and are not direct experimental quasiparticle spectra.",
            "Only compact metadata is returned here; the full pymatgen object is intentionally not serialized.",
        ],
    }


def _fetch_band_structure_payload(mpr: Any, material_id: str) -> dict[str, Any]:
    try:
        band_structure = None
        getter = getattr(mpr, "get_bandstructure_by_material_id", None)
        if callable(getter):
            band_structure = getter(material_id)
        if band_structure is None:
            rester = getattr(getattr(mpr, "materials", None), "electronic_structure_bandstructure", None)
            getter = getattr(rester, "get_bandstructure_from_material_id", None)
            if callable(getter):
                band_structure = getter(material_id)
        if band_structure is None:
            raise MaterialsDependencyError("No band-structure getter is available in mp-api")
        return _band_structure_payload(band_structure)
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "limitations": [
                "No band-structure payload was returned for this material, or the upstream API could not provide it.",
            ],
        }


def _dos_density_arrays(dos: Any) -> list[list[float]]:
    densities = getattr(dos, "densities", {}) or {}
    if isinstance(densities, dict):
        return [_numeric_sequence(values) for values in densities.values()]
    values = _numeric_sequence(densities)
    return [values] if values else []


def _dos_payload(dos: Any) -> dict[str, Any]:
    energies = _numeric_sequence(getattr(dos, "energies", None))
    density_arrays = _dos_density_arrays(dos)
    energy_count = len(energies)
    total_density: list[float] = []
    if density_arrays and energy_count:
        for index in range(energy_count):
            total_density.append(
                sum(values[index] for values in density_arrays if index < len(values))
            )

    element_symbols: list[str] = []
    element_dos = _safe_call(dos, "get_element_dos")
    if isinstance(element_dos, dict):
        element_symbols = [str(element) for element in list(element_dos.keys())[:24]]

    cbm_vbm = _as_plain(_safe_call(dos, "get_cbm_vbm"))
    band_gap = _safe_number(_safe_call(dos, "get_gap"))
    return {
        "available": True,
        "object": type(dos).__name__,
        "efermi_ev": _safe_number(getattr(dos, "efermi", None)),
        "energy_count": energy_count,
        "energy_range_ev": [
            round(min(energies), 6),
            round(max(energies), 6),
        ] if energies else None,
        "spin_channel_count": len(density_arrays),
        "band_gap_ev": band_gap,
        "cbm_vbm": cbm_vbm,
        "element_projections": element_symbols,
        "visualization": {
            "type": "density_of_states",
            "x_axis": "energy_ev",
            "y_axis": "density",
            "series": _downsample_xy(energies, total_density),
            "truncated": len(energies) > 160,
        },
        "data_quality": {
            "computed_from": "materials_project_uniform_nscf_density_of_states",
            "external_database_lookup": True,
            "experimental": False,
        },
        "limitations": [
            "DOS values are computed DFT data and may not align exactly with line-mode band-structure gaps.",
            "The visualization is downsampled for payload size; the full pymatgen object is intentionally not serialized.",
        ],
    }


def _fetch_dos_payload(mpr: Any, material_id: str) -> dict[str, Any]:
    try:
        dos = None
        getter = getattr(mpr, "get_dos_by_material_id", None)
        if callable(getter):
            dos = getter(material_id)
        if dos is None:
            rester = getattr(getattr(mpr, "materials", None), "electronic_structure_dos", None)
            getter = getattr(rester, "get_dos_from_material_id", None)
            if callable(getter):
                dos = getter(material_id)
        if dos is None:
            raise MaterialsDependencyError("No DOS getter is available in mp-api")
        return _dos_payload(dos)
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "limitations": [
                "No density-of-states payload was returned for this material, or the upstream API could not provide it.",
            ],
        }


def _first_optional_record(section: dict[str, Any]) -> dict[str, Any]:
    records = section.get("records")
    if isinstance(records, list) and records and isinstance(records[0], dict):
        return records[0]
    return {}


def _section_availability(evidence: dict[str, Any]) -> dict[str, bool]:
    availability: dict[str, bool] = {}
    for key, section in evidence.items():
        if isinstance(section, dict):
            availability[key] = bool(section.get("available"))
    return availability


def _build_deep_report(
    *,
    summary: dict[str, Any],
    selection: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    thermo = _first_optional_record(evidence.get("thermo", {}) if isinstance(evidence.get("thermo"), dict) else {})
    electronic = _first_optional_record(
        evidence.get("electronic_structure", {}) if isinstance(evidence.get("electronic_structure"), dict) else {}
    )
    elasticity = _first_optional_record(evidence.get("elasticity", {}) if isinstance(evidence.get("elasticity"), dict) else {})
    band_structure = evidence.get("band_structure") if isinstance(evidence.get("band_structure"), dict) else {}
    dos = evidence.get("density_of_states") if isinstance(evidence.get("density_of_states"), dict) else {}

    highlights = [
        {
            "label": "Selected material",
            "value": summary.get("material_id"),
            "detail": selection.get("selected_reason"),
        },
        {
            "label": "Stability",
            "value": summary.get("is_stable"),
            "detail": f"Hull {summary.get('energy_above_hull_ev_atom')} eV/atom",
        },
        {
            "label": "Electronic gap",
            "value": summary.get("band_gap_ev") if summary.get("band_gap_ev") is not None else electronic.get("band_gap"),
            "detail": "eV, computed database value",
        },
        {
            "label": "Elastic data",
            "value": "available" if evidence.get("elasticity", {}).get("available") else "unavailable",
            "detail": f"K_VRH {elasticity.get('k_vrh', elasticity.get('bulk_modulus'))}",
        },
    ]

    sections = [
        {
            "key": "summary",
            "title": "Summary",
            "status": "available",
            "highlights": [
                f"Formula: {summary.get('formula_pretty')}",
                f"Symmetry: {(summary.get('symmetry') or {}).get('symbol') if isinstance(summary.get('symmetry'), dict) else None}",
            ],
        },
        {
            "key": "thermo",
            "title": "Thermodynamics",
            "status": "available" if evidence.get("thermo", {}).get("available") else "unavailable",
            "highlights": [
                f"Formation energy: {summary.get('formation_energy_ev_atom') if summary.get('formation_energy_ev_atom') is not None else thermo.get('formation_energy_per_atom')} eV/atom",
                f"Energy above hull: {summary.get('energy_above_hull_ev_atom') if summary.get('energy_above_hull_ev_atom') is not None else thermo.get('energy_above_hull')} eV/atom",
            ],
        },
        {
            "key": "band_structure",
            "title": "Band Structure",
            "status": "available" if band_structure.get("available") else "unavailable",
            "highlights": [
                f"Band count: {band_structure.get('band_count')}",
                f"K-points: {band_structure.get('kpoint_count')}",
            ],
        },
        {
            "key": "density_of_states",
            "title": "Density of States",
            "status": "available" if dos.get("available") else "unavailable",
            "highlights": [
                f"Energy grid: {dos.get('energy_count')}",
                f"Projected elements: {', '.join(dos.get('element_projections') or [])}",
            ],
        },
        {
            "key": "elasticity",
            "title": "Elastic Constants",
            "status": "available" if evidence.get("elasticity", {}).get("available") else "unavailable",
            "highlights": [
                f"Bulk modulus: {elasticity.get('k_vrh', elasticity.get('bulk_modulus'))}",
                f"Shear modulus: {elasticity.get('g_vrh', elasticity.get('shear_modulus'))}",
                f"Poisson ratio: {elasticity.get('poisson_ratio', elasticity.get('homogeneous_poisson'))}",
            ],
        },
    ]

    return {
        "title": f"Materials Project deep dossier: {summary.get('formula_pretty') or summary.get('material_id')}",
        "material_id": summary.get("material_id"),
        "formula": summary.get("formula_pretty"),
        "selection_strategy": selection.get("strategy"),
        "availability": _section_availability(evidence),
        "highlights": highlights,
        "sections": sections,
    }


def materials_project_deep_profile(
    *,
    formula: Any = None,
    material_id: Any = None,
    chemical_system: Any = None,
    include_structure: bool = True,
    include_thermo: bool = True,
    include_electronic: bool = True,
    include_dielectric: bool = True,
    include_band_structure: bool = True,
    include_dos: bool = True,
    include_elasticity: bool = True,
) -> dict[str, Any]:
    """Build a single-material Materials Project dossier with heavy evidence summaries."""

    MPRester = _require_mprester()
    with MPRester(_get_api_key(), mute_progress_bars=True) as mpr:
        selection_payload = _select_material_profile_summary(
            mpr,
            formula=formula,
            material_id=material_id,
            chemical_system=chemical_system,
        )
        query = selection_payload["query"]
        if not selection_payload["found"]:
            return {
                "success": True,
                "version": "1.0",
                "source": "Materials Project",
                "engine": "mp-api+pymatgen",
                "query": query,
                "profile_status": "not_found",
                "deep_profile_status": "not_found",
                "count": 0,
                "profile": None,
                "selection": None,
                "evidence": {},
                "report": None,
                "data_quality": {
                    "computed_from": "materials_project_database",
                    "external_database_lookup": True,
                    "experimental": False,
                },
                "limitations": [
                    "No Materials Project record matched the query.",
                    "Absence from this lookup is not evidence that the material cannot exist.",
                ],
            }

        summary = selection_payload["summary"]
        selected_material_id = str(selection_payload["selected_material_id"])
        selection = selection_payload["selection"]
        evidence: dict[str, Any] = {}

        if include_structure:
            try:
                structure = mpr.materials.get_structure_by_material_id(selected_material_id)
                evidence["structure"] = _structure_payload(structure)
            except Exception as exc:
                evidence["structure"] = {"available": False, "error": str(exc)}

        if include_thermo:
            evidence["thermo"] = _search_optional_rester(
                mpr.materials.thermo,
                material_id=selected_material_id,
                fields=THERMO_FIELDS,
            )

        if include_electronic:
            evidence["electronic_structure"] = _search_optional_rester(
                mpr.materials.electronic_structure,
                material_id=selected_material_id,
                fields=ELECTRONIC_FIELDS,
            )

        if include_dielectric:
            evidence["dielectric"] = _search_optional_rester(
                mpr.materials.dielectric,
                material_id=selected_material_id,
                fields=DIELECTRIC_FIELDS,
            )

        if include_band_structure:
            evidence["band_structure"] = _fetch_band_structure_payload(
                mpr,
                selected_material_id,
            )

        if include_dos:
            evidence["density_of_states"] = _fetch_dos_payload(
                mpr,
                selected_material_id,
            )

        if include_elasticity:
            evidence["elasticity"] = _search_optional_rester(
                mpr.materials.elasticity,
                material_id=selected_material_id,
                fields=ELASTICITY_FIELDS,
                max_records=1,
            )

    return {
        "success": True,
        "version": "1.0",
        "source": "Materials Project",
        "engine": "mp-api+pymatgen",
        "query": query,
        "profile_status": "ready",
        "deep_profile_status": "ready",
        "count": 1,
        "material_id": selected_material_id,
        "profile": summary,
        "selection": selection,
        "evidence": evidence,
        "report": _build_deep_report(
            summary=summary,
            selection=selection or {},
            evidence=evidence,
        ),
        "data_quality": {
            "computed_from": "materials_project_database_and_pymatgen_objects",
            "external_database_lookup": True,
            "experimental": False,
        },
        "limitations": [
            "Materials Project values are computed database results and can change with database releases.",
            "Band structure and DOS sections summarize pymatgen objects; full arrays are not serialized in this lightweight API response.",
            "Unavailable evidence sections indicate no returned record or an upstream API error; no substitute values are fabricated.",
            "DFT band gaps and elastic constants should be treated as computed evidence, not experimental validation.",
        ],
    }
