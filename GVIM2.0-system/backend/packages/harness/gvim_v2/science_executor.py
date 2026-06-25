"""Natural-language scientific tool execution for the v2 SaaS surface.

The LLM is used only to choose a whitelisted tool and build structured
arguments. Package-backed chemistry and materials functions perform all
scientific computation.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from gvim_v2.chemistry.capabilities import build_chemistry_capabilities_payload
from gvim_v2.chemistry.ketcher_commands import (
    KETCHER_STRUCTURE_COMMAND_TYPES,
    first_structure_command,
    ketcher_commands_from_payload,
    with_ketcher_commands,
)
from gvim_v2.chemistry.llm_json import post_chemistry_llm_json
from gvim_v2.chemistry.rdkit_3d import build_rdkit_conformer_payload
from gvim_v2.chemistry.rdkit_descriptors import build_rdkit_descriptor_payload
from gvim_v2.chemistry.rdkit_reaction_tools import (
    build_reaction_qc_payload,
    build_substructure_search_payload,
)
from gvim_v2.chemistry.rdkit_similarity import build_similarity_payload
from gvim_v2.chemistry.rdkit_structure_ops import (
    build_fragmentation_payload,
    build_standardization_payload,
)
from gvim_v2.chemistry.structure_resolution import build_structure_resolution_payload
from gvim_v2.chemistry.studio_preparation import build_studio_preparation_payload
from gvim_v2.materials import (
    analyze_formula,
    analyze_local_environment,
    analyze_structure,
    batch_composition_features,
    composition_features,
    convert_unit,
    correct_spectrum_baseline,
    describe_structure_with_robocrys,
    detect_spectrum_peaks,
    element_properties,
    fit_spectrum_peaks,
    generate_pyxtal_structures,
    high_symmetry_kpath,
    match_structures,
    match_xrd_peaks,
    materials_project_deep_profile,
    materials_project_profile,
    plan_precursors,
    quality_check_structure,
    resolve_pubchem_compound,
    scattering_reference_data,
    screen_formulas,
    search_materials_project,
    search_optimade_structures,
    simulate_and_match_xrd,
    simulate_xrd,
    transform_structure,
    xray_reference_data,
)
from gvim_v2.materials.errors import MaterialsDependencyError

JsonDict = dict[str, Any]
ToolRunner = Callable[[JsonDict], JsonDict]


@dataclass(frozen=True)
class ScienceTool:
    key: str
    domain: str
    description: str
    input_schema: JsonDict
    runner: ToolRunner
    required: tuple[str, ...] = ()
    required_any: tuple[tuple[str, ...], ...] = ()

    def public_spec(self) -> JsonDict:
        return {
            "key": self.key,
            "domain": self.domain,
            "description": self.description,
            "input_schema": deepcopy(self.input_schema),
            "required": list(self.required),
            "required_any": [list(group) for group in self.required_any],
        }


def _arg(args: JsonDict, key: str, default: Any = None) -> Any:
    return args.get(key, default)


def _run_chemistry_studio_prepare(args: JsonDict) -> JsonDict:
    return build_studio_preparation_payload(
        _arg(args, "query"),
        allow_pubchem=bool(_arg(args, "allow_pubchem", True)),
        timeout=float(_arg(args, "timeout", 90.0) or 90.0),
    )


def _run_structure_resolver(args: JsonDict) -> JsonDict:
    return build_structure_resolution_payload(
        _arg(args, "query"),
        allow_pubchem=bool(_arg(args, "allow_pubchem", True)),
        timeout=float(_arg(args, "timeout", 10.0) or 10.0),
    )


def _run_rdkit_descriptors(args: JsonDict) -> JsonDict:
    return build_rdkit_descriptor_payload(
        _arg(args, "smiles"),
        _arg(args, "analysis_type", "rdkit_descriptors"),
    )


def _run_similarity(args: JsonDict) -> JsonDict:
    return build_similarity_payload(
        _arg(args, "smiles_list"),
        radius=_arg(args, "radius", 2),
        n_bits=_arg(args, "n_bits", 2048),
    )


def _run_reaction_qc(args: JsonDict) -> JsonDict:
    return build_reaction_qc_payload(_arg(args, "reaction") or _arg(args, "reaction_smiles"))


def _run_substructure(args: JsonDict) -> JsonDict:
    return build_substructure_search_payload(
        _arg(args, "smiles_list"),
        _arg(args, "smarts"),
        labels=_arg(args, "labels"),
        max_matches_per_molecule=_arg(args, "max_matches_per_molecule", 20),
    )


def _run_conformer(args: JsonDict) -> JsonDict:
    return build_rdkit_conformer_payload(
        _arg(args, "smiles"),
        num_conformers=_arg(args, "num_conformers", 3),
        max_iterations=_arg(args, "max_iterations", 300),
    )


def _run_formula_analysis(args: JsonDict) -> JsonDict:
    return analyze_formula(_arg(args, "formula"))


def _run_formula_screening(args: JsonDict) -> JsonDict:
    return screen_formulas(
        _arg(args, "formulas"),
        target_application=str(_arg(args, "target_application", "") or ""),
    )


def _run_xrd_peak_match(args: JsonDict) -> JsonDict:
    return match_xrd_peaks(
        observed_peaks=_arg(args, "observed_peaks"),
        reference_peaks=_arg(args, "reference_peaks"),
        tolerance_two_theta=float(_arg(args, "tolerance_two_theta", 0.25) or 0.25),
    )


def _run_structure_analysis(args: JsonDict) -> JsonDict:
    return analyze_structure(
        _arg(args, "structure_text"),
        file_format=_arg(args, "file_format", "auto"),
        symprec=float(_arg(args, "symprec", 0.1) or 0.1),
    )


def _run_structure_qc(args: JsonDict) -> JsonDict:
    return quality_check_structure(
        _arg(args, "structure_text"),
        file_format=_arg(args, "file_format", "auto"),
        symprec=float(_arg(args, "symprec", 0.1) or 0.1),
        min_distance_threshold=float(_arg(args, "min_distance_threshold", 0.6) or 0.6),
        max_sites=int(_arg(args, "max_sites", 512) or 512),
    )


def _run_structure_transform(args: JsonDict) -> JsonDict:
    return transform_structure(
        _arg(args, "structure_text"),
        file_format=_arg(args, "file_format", "auto"),
        output_format=_arg(args, "output_format", "cif"),
        make_primitive=bool(_arg(args, "make_primitive", False)),
        make_conventional=bool(_arg(args, "make_conventional", False)),
        supercell_matrix=_arg(args, "supercell_matrix"),
        symprec=float(_arg(args, "symprec", 0.1) or 0.1),
        max_sites=int(_arg(args, "max_sites", 512) or 512),
    )


def _run_structure_description(args: JsonDict) -> JsonDict:
    return describe_structure_with_robocrys(
        _arg(args, "structure_text"),
        file_format=_arg(args, "file_format", "auto"),
        symprec=float(_arg(args, "symprec", 0.1) or 0.1),
        max_sites=int(_arg(args, "max_sites", 256) or 256),
        include_mineral_match=bool(_arg(args, "include_mineral_match", False)),
    )


def _run_pyxtal_generation(args: JsonDict) -> JsonDict:
    return generate_pyxtal_structures(
        _arg(args, "formula"),
        _arg(args, "space_group") or _arg(args, "spacegroup"),
        dimensionality=int(_arg(args, "dimensionality", 3) or 3),
        candidate_count=int(_arg(args, "candidate_count", 1) or 1),
        formula_units=_arg(args, "formula_units"),
        max_formula_units=int(_arg(args, "max_formula_units", 12) or 12),
        max_sites=int(_arg(args, "max_sites", 128) or 128),
        max_attempts=int(_arg(args, "max_attempts", 30) or 30),
        seed=_arg(args, "seed"),
        output_format=_arg(args, "output_format", "cif"),
        symprec=float(_arg(args, "symprec", 0.1) or 0.1),
    )


def _run_local_environment(args: JsonDict) -> JsonDict:
    return analyze_local_environment(
        _arg(args, "structure_text"),
        file_format=_arg(args, "file_format", "auto"),
        method=_arg(args, "method", "crystal_nn"),
        symprec=float(_arg(args, "symprec", 0.1) or 0.1),
        max_sites=int(_arg(args, "max_sites", 128) or 128),
        max_neighbors_per_site=int(_arg(args, "max_neighbors_per_site", 16) or 16),
    )


def _run_structure_match(args: JsonDict) -> JsonDict:
    return match_structures(
        _arg(args, "structure_text_a"),
        _arg(args, "structure_text_b"),
        file_format_a=_arg(args, "file_format_a", "auto"),
        file_format_b=_arg(args, "file_format_b", "auto"),
        ltol=float(_arg(args, "ltol", 0.2) or 0.2),
        stol=float(_arg(args, "stol", 0.3) or 0.3),
        angle_tol=float(_arg(args, "angle_tol", 5.0) or 5.0),
        primitive_cell=bool(_arg(args, "primitive_cell", True)),
        scale=bool(_arg(args, "scale", True)),
    )


def _run_xrd_simulation(args: JsonDict) -> JsonDict:
    return simulate_xrd(
        _arg(args, "structure_text"),
        file_format=_arg(args, "file_format", "auto"),
        wavelength=_arg(args, "wavelength", "CuKa"),
        two_theta_min=float(_arg(args, "two_theta_min", 5.0) or 5.0),
        two_theta_max=float(_arg(args, "two_theta_max", 90.0) or 90.0),
        min_relative_intensity=float(_arg(args, "min_relative_intensity", 1.0) or 1.0),
        max_peaks=int(_arg(args, "max_peaks", 120) or 120),
    )


def _run_xrd_simulate_match(args: JsonDict) -> JsonDict:
    return simulate_and_match_xrd(
        _arg(args, "structure_text"),
        observed_peaks=_arg(args, "observed_peaks"),
        file_format=_arg(args, "file_format", "auto"),
        tolerance_two_theta=float(_arg(args, "tolerance_two_theta", 0.25) or 0.25),
        wavelength=_arg(args, "wavelength", "CuKa"),
        two_theta_min=float(_arg(args, "two_theta_min", 5.0) or 5.0),
        two_theta_max=float(_arg(args, "two_theta_max", 90.0) or 90.0),
        min_relative_intensity=float(_arg(args, "min_relative_intensity", 5.0) or 5.0),
    )


def _run_precursor_planning(args: JsonDict) -> JsonDict:
    return plan_precursors(
        target_formula=_arg(args, "target_formula") or _arg(args, "formula"),
        target_mass_g=_arg(args, "target_mass_g"),
        precursors=_arg(args, "precursors"),
        basis_elements=_arg(args, "basis_elements"),
    )


def _run_elements(args: JsonDict) -> JsonDict:
    return element_properties(formula=_arg(args, "formula"), elements=_arg(args, "elements"))


def _run_composition_features(args: JsonDict) -> JsonDict:
    max_features = _arg(args, "max_features")
    return composition_features(
        _arg(args, "formula"),
        max_features=int(max_features) if max_features not in (None, "") else None,
    )


def _run_batch_composition_features(args: JsonDict) -> JsonDict:
    max_features = _arg(args, "max_features")
    return batch_composition_features(
        _arg(args, "formulas"),
        max_features=int(max_features) if max_features not in (None, "") else None,
        include_csv=bool(_arg(args, "include_csv", True)),
    )


def _run_unit_conversion(args: JsonDict) -> JsonDict:
    return convert_unit(
        value=_arg(args, "value"),
        from_unit=_arg(args, "from_unit"),
        to_unit=_arg(args, "to_unit"),
        per_mole=bool(_arg(args, "per_mole", False)),
    )


def _run_spectrum_baseline(args: JsonDict) -> JsonDict:
    return correct_spectrum_baseline(
        x_values=_arg(args, "x_values"),
        y_values=_arg(args, "y_values"),
        xy_text=_arg(args, "xy_text"),
        method=_arg(args, "method", "asls"),
        lam=float(_arg(args, "lam", 100000.0) or 100000.0),
        p=float(_arg(args, "p", 0.01) or 0.01),
    )


def _run_peak_detection(args: JsonDict) -> JsonDict:
    return detect_spectrum_peaks(
        x_values=_arg(args, "x_values"),
        y_values=_arg(args, "y_values"),
        xy_text=_arg(args, "xy_text"),
        prominence=_arg(args, "prominence"),
        height=_arg(args, "height"),
        distance=_arg(args, "distance"),
        max_peaks=int(_arg(args, "max_peaks", 50) or 50),
    )


def _run_peak_fit(args: JsonDict) -> JsonDict:
    return fit_spectrum_peaks(
        x_values=_arg(args, "x_values"),
        y_values=_arg(args, "y_values"),
        xy_text=_arg(args, "xy_text"),
        peak_positions=_arg(args, "peak_positions"),
        model=_arg(args, "model", "gaussian"),
        max_peaks=int(_arg(args, "max_peaks", 5) or 5),
        prominence=_arg(args, "prominence"),
    )


def _run_kpath(args: JsonDict) -> JsonDict:
    return high_symmetry_kpath(
        _arg(args, "structure_text"),
        file_format=_arg(args, "file_format", "auto"),
        symprec=float(_arg(args, "symprec", 0.1) or 0.1),
    )


def _run_pubchem(args: JsonDict) -> JsonDict:
    return resolve_pubchem_compound(
        _arg(args, "query") or _arg(args, "name") or _arg(args, "smiles") or _arg(args, "cid"),
        namespace=_arg(args, "namespace", "name"),
        limit=int(_arg(args, "limit", 5) or 5),
    )


def _run_optimade(args: JsonDict) -> JsonDict:
    return search_optimade_structures(
        formula=_arg(args, "formula"),
        elements=_arg(args, "elements"),
        provider_url=_arg(args, "provider_url"),
        limit=int(_arg(args, "limit", 5) or 5),
    )


def _run_xray(args: JsonDict) -> JsonDict:
    return xray_reference_data(
        formula=_arg(args, "formula"),
        elements=_arg(args, "elements"),
        edge=_arg(args, "edge", "K"),
        max_lines=int(_arg(args, "max_lines", 8) or 8),
    )


def _run_scattering(args: JsonDict) -> JsonDict:
    return scattering_reference_data(formula=_arg(args, "formula"), elements=_arg(args, "elements"))


def _run_materials_project_search(args: JsonDict) -> JsonDict:
    return search_materials_project(
        formula=_arg(args, "formula"),
        elements=_arg(args, "elements"),
        material_ids=_arg(args, "material_ids"),
        chemical_system=_arg(args, "chemical_system") or _arg(args, "chemsys"),
        is_stable=_arg(args, "is_stable"),
        band_gap=_arg(args, "band_gap"),
        energy_above_hull=_arg(args, "energy_above_hull"),
        limit=int(_arg(args, "limit", 10) or 10),
    )


def _run_materials_project_profile(args: JsonDict) -> JsonDict:
    return materials_project_profile(
        formula=_arg(args, "formula"),
        material_id=_arg(args, "material_id") or _arg(args, "material_ids"),
        chemical_system=_arg(args, "chemical_system") or _arg(args, "chemsys"),
        include_thermo=bool(_arg(args, "include_thermo", True)),
        include_electronic=bool(_arg(args, "include_electronic", True)),
        include_dielectric=bool(_arg(args, "include_dielectric", True)),
        include_structure=bool(_arg(args, "include_structure", True)),
    )


def _run_materials_project_deep_profile(args: JsonDict) -> JsonDict:
    return materials_project_deep_profile(
        formula=_arg(args, "formula"),
        material_id=_arg(args, "material_id") or _arg(args, "material_ids"),
        chemical_system=_arg(args, "chemical_system") or _arg(args, "chemsys"),
        include_structure=bool(_arg(args, "include_structure", True)),
        include_thermo=bool(_arg(args, "include_thermo", True)),
        include_electronic=bool(_arg(args, "include_electronic", True)),
        include_dielectric=bool(_arg(args, "include_dielectric", True)),
        include_band_structure=bool(_arg(args, "include_band_structure", True)),
        include_dos=bool(_arg(args, "include_dos", True)),
        include_elasticity=bool(_arg(args, "include_elasticity", True)),
    )


SCIENCE_TOOLS: dict[str, ScienceTool] = {
    "chemistry_studio_prepare": ScienceTool(
        "chemistry_studio_prepare",
        "chemistry",
        (
            "Prepare native KetcherCommand objects from a molecule, reaction, route, "
            "or editor operation request; use for draw/sketch/load/open/edit canvas requests."
        ),
        {
            "query": "natural-language drawing or Ketcher editor command request",
            "allow_pubchem": "boolean optional",
        },
        _run_chemistry_studio_prepare,
        required=("query",),
    ),
    "structure_resolver": ScienceTool(
        "structure_resolver",
        "chemistry",
        "Resolve a molecule name, Chinese common name, CAS-like text, or SMILES to structure data; intermediate helper, not a Ketcher or 3D deliverable.",
        {"query": "compound name or SMILES", "allow_pubchem": "boolean optional"},
        _run_structure_resolver,
        required=("query",),
    ),
    "rdkit_descriptors": ScienceTool(
        "rdkit_descriptors",
        "chemistry",
        "Compute RDKit numeric molecular descriptors from a validated SMILES string.",
        {"smiles": "SMILES"},
        _run_rdkit_descriptors,
        required=("smiles",),
    ),
    "rdkit_similarity": ScienceTool(
        "rdkit_similarity",
        "chemistry",
        "Compare 2-8 molecules using Morgan fingerprints and Tanimoto similarity.",
        {"smiles_list": "list of 2-8 SMILES", "radius": "1-4 optional"},
        _run_similarity,
        required=("smiles_list",),
    ),
    "rdkit_reaction_qc": ScienceTool(
        "rdkit_reaction_qc",
        "chemistry",
        "Check reaction SMILES for element balance, charge balance, and atom-map coverage.",
        {"reaction": "reaction SMILES such as A.B>>C.D"},
        _run_reaction_qc,
        required=("reaction",),
    ),
    "rdkit_substructure_search": ScienceTool(
        "rdkit_substructure_search",
        "chemistry",
        "Search molecules with a SMARTS query and return matching atom indices.",
        {"smiles_list": "list of SMILES", "smarts": "SMARTS query", "labels": "optional list"},
        _run_substructure,
        required=("smiles_list", "smarts"),
    ),
    "rdkit_standardization": ScienceTool(
        "rdkit_standardization",
        "chemistry",
        "Standardize a molecule with RDKit cleanup, parent selection, uncharging, and tautomer handling.",
        {"smiles": "SMILES"},
        lambda args: build_standardization_payload(_arg(args, "smiles")),
        required=("smiles",),
    ),
    "rdkit_fragmentation": ScienceTool(
        "rdkit_fragmentation",
        "chemistry",
        "Extract Murcko scaffold and BRICS fragments.",
        {"smiles": "SMILES"},
        lambda args: build_fragmentation_payload(_arg(args, "smiles")),
        required=("smiles",),
    ),
    "rdkit_3d_conformer": ScienceTool(
        "rdkit_3d_conformer",
        "chemistry",
        "Generate a native 3Dmol/RDKit ETKDG 3D conformer artifact for a small molecule.",
        {"smiles": "SMILES", "num_conformers": "optional integer"},
        _run_conformer,
        required=("smiles",),
    ),
    "formula_analysis": ScienceTool(
        "formula_analysis",
        "materials",
        "Parse a formula and compute composition descriptors.",
        {"formula": "materials formula"},
        _run_formula_analysis,
        required=("formula",),
    ),
    "formula_screening": ScienceTool(
        "formula_screening",
        "materials",
        "Parse and validate a small list of formulas without unsupported application ranking.",
        {"formulas": "list of formulas", "target_application": "optional text"},
        _run_formula_screening,
        required=("formulas",),
    ),
    "xrd_peak_match": ScienceTool(
        "xrd_peak_match",
        "materials",
        "Match observed and reference XRD peak positions.",
        {"observed_peaks": "list", "reference_peaks": "list", "tolerance_two_theta": "optional"},
        _run_xrd_peak_match,
        required=("observed_peaks", "reference_peaks"),
    ),
    "structure_analysis": ScienceTool(
        "structure_analysis",
        "materials",
        "Parse CIF/POSCAR/XYZ and summarize formula, lattice, density, and space group.",
        {"structure_text": "CIF/POSCAR/XYZ text", "file_format": "auto|cif|poscar|xyz"},
        _run_structure_analysis,
        required=("structure_text",),
    ),
    "structure_qc": ScienceTool(
        "structure_qc",
        "materials",
        "Run lightweight CIF/POSCAR quality checks for parsing, short distances, disorder, and symmetry.",
        {"structure_text": "CIF/POSCAR text", "file_format": "auto|cif|poscar"},
        _run_structure_qc,
        required=("structure_text",),
    ),
    "structure_transform": ScienceTool(
        "structure_transform",
        "materials",
        "Convert CIF/POSCAR and optionally generate primitive, conventional, or supercell structures.",
        {"structure_text": "CIF/POSCAR text", "output_format": "cif|poscar|json", "supercell_matrix": "optional"},
        _run_structure_transform,
        required=("structure_text",),
    ),
    "structure_description": ScienceTool(
        "structure_description",
        "materials",
        "Describe a CIF/POSCAR crystal structure with robocrys. Oxidation-state text is disabled by default.",
        {"structure_text": "CIF/POSCAR text", "file_format": "auto|cif|poscar", "include_mineral_match": "optional boolean"},
        _run_structure_description,
        required=("structure_text",),
    ),
    "pyxtal_structure_generation": ScienceTool(
        "pyxtal_structure_generation",
        "materials",
        "Generate small symmetry-constrained candidate crystal structures with PyXtal. Results are candidates, not stability or synthesis evidence.",
        {"formula": "formula such as NaCl", "space_group": "space-group number or exact symbol", "candidate_count": "optional 1-5"},
        _run_pyxtal_generation,
        required=("formula", "space_group"),
    ),
    "structure_local_environment": ScienceTool(
        "structure_local_environment",
        "materials",
        "Compute coordination environments and neighbor tables for a periodic structure.",
        {"structure_text": "CIF/POSCAR text", "method": "crystal_nn|minimum_distance"},
        _run_local_environment,
        required=("structure_text",),
    ),
    "structure_matcher": ScienceTool(
        "structure_matcher",
        "materials",
        "Compare two periodic structures for crystallographic equivalence.",
        {"structure_text_a": "CIF/POSCAR", "structure_text_b": "CIF/POSCAR"},
        _run_structure_match,
        required=("structure_text_a", "structure_text_b"),
    ),
    "xrd_simulation": ScienceTool(
        "xrd_simulation",
        "materials",
        "Simulate theoretical powder XRD from a CIF/POSCAR structure.",
        {"structure_text": "CIF/POSCAR text", "wavelength": "optional"},
        _run_xrd_simulation,
        required=("structure_text",),
    ),
    "xrd_simulate_match": ScienceTool(
        "xrd_simulate_match",
        "materials",
        "Simulate XRD from a structure and match observed experimental peaks.",
        {"structure_text": "CIF/POSCAR text", "observed_peaks": "list"},
        _run_xrd_simulate_match,
        required=("structure_text", "observed_peaks"),
    ),
    "precursor_planning": ScienceTool(
        "precursor_planning",
        "materials",
        "Compute precursor stoichiometry and weighing masses.",
        {"target_formula": "formula", "target_mass_g": "number", "precursors": "list"},
        _run_precursor_planning,
        required=("target_formula", "target_mass_g", "precursors"),
    ),
    "element_properties": ScienceTool(
        "element_properties",
        "materials",
        "Return periodic-table descriptors for formula elements or explicit symbols.",
        {"formula": "formula optional", "elements": "list optional"},
        _run_elements,
        required_any=(("formula", "elements"),),
    ),
    "composition_features": ScienceTool(
        "composition_features",
        "materials",
        "Compute matminer composition descriptors for one formula.",
        {"formula": "formula", "max_features": "optional integer"},
        _run_composition_features,
        required=("formula",),
    ),
    "composition_feature_table": ScienceTool(
        "composition_feature_table",
        "materials",
        "Compute a rectangular matminer composition descriptor table for up to 50 formulas.",
        {"formulas": "list of formulas", "max_features": "optional integer", "include_csv": "optional boolean"},
        _run_batch_composition_features,
        required=("formulas",),
    ),
    "unit_conversion": ScienceTool(
        "unit_conversion",
        "materials",
        "Convert scientific units with pint.",
        {"value": "number", "from_unit": "unit", "to_unit": "unit", "per_mole": "boolean optional"},
        _run_unit_conversion,
        required=("value", "from_unit", "to_unit"),
    ),
    "spectrum_baseline": ScienceTool(
        "spectrum_baseline",
        "materials",
        "Baseline-correct small XY spectra.",
        {"xy_text": "text optional", "x_values": "list optional", "y_values": "list optional"},
        _run_spectrum_baseline,
        required_any=(("xy_text",), ("x_values", "y_values")),
    ),
    "spectrum_peak_detection": ScienceTool(
        "spectrum_peak_detection",
        "materials",
        "Detect peaks in small XY spectra.",
        {"xy_text": "text optional", "x_values": "list optional", "y_values": "list optional"},
        _run_peak_detection,
        required_any=(("xy_text",), ("x_values", "y_values")),
    ),
    "spectrum_peak_fit": ScienceTool(
        "spectrum_peak_fit",
        "materials",
        "Fit Gaussian, Lorentzian, or Voigt peak models to XY spectra.",
        {"xy_text": "text optional", "x_values": "list optional", "y_values": "list optional", "peak_positions": "optional list"},
        _run_peak_fit,
        required_any=(("xy_text",), ("x_values", "y_values")),
    ),
    "high_symmetry_kpath": ScienceTool(
        "high_symmetry_kpath",
        "materials",
        "Generate a standardized high-symmetry reciprocal-space k-path.",
        {"structure_text": "CIF/POSCAR text"},
        _run_kpath,
        required=("structure_text",),
    ),
    "pubchem_resolve": ScienceTool(
        "pubchem_resolve",
        "materials",
        "Resolve small-molecule names, identifiers, or SMILES through PubChem.",
        {"query": "name, CID, InChI, InChIKey, or SMILES", "namespace": "optional"},
        _run_pubchem,
        required=("query",),
    ),
    "optimade_structure_search": ScienceTool(
        "optimade_structure_search",
        "materials",
        "Search an OPTIMADE structures endpoint by formula or elements.",
        {"formula": "formula optional", "elements": "list optional"},
        _run_optimade,
        required_any=(("formula",), ("elements",)),
    ),
    "xray_reference": ScienceTool(
        "xray_reference",
        "materials",
        "Return X-ray absorption edges and emission-line references for elements.",
        {"formula": "formula optional", "elements": "list optional", "edge": "optional"},
        _run_xray,
        required_any=(("formula",), ("elements",)),
    ),
    "scattering_reference": ScienceTool(
        "scattering_reference",
        "materials",
        "Return neutron scattering and element reference rows.",
        {"formula": "formula optional", "elements": "list optional"},
        _run_scattering,
        required_any=(("formula",), ("elements",)),
    ),
    "materials_project_search": ScienceTool(
        "materials_project_search",
        "materials",
        "Search real Materials Project summary data. Requires MP_API_KEY.",
        {"formula": "formula optional", "elements": "list optional", "material_ids": "optional"},
        _run_materials_project_search,
        required_any=(("formula",), ("elements",), ("material_ids",), ("chemical_system",)),
    ),
    "materials_project_profile": ScienceTool(
        "materials_project_profile",
        "materials",
        "Build a compact Materials Project evidence profile. Requires MP_API_KEY.",
        {"formula": "formula optional", "material_id": "optional", "chemical_system": "optional"},
        _run_materials_project_profile,
        required_any=(("formula",), ("material_id",), ("material_ids",), ("chemical_system",)),
    ),
    "materials_project_deep_profile": ScienceTool(
        "materials_project_deep_profile",
        "materials",
        "Build a deep Materials Project dossier with band-structure, DOS, elastic, thermo, electronic, dielectric, and structure evidence when available. Requires MP_API_KEY.",
        {"formula": "formula optional", "material_id": "optional", "chemical_system": "optional"},
        _run_materials_project_deep_profile,
        required_any=(("formula",), ("material_id",), ("material_ids",), ("chemical_system",)),
    ),
}


CONTEXT_ARG_ALIASES: dict[str, tuple[str, ...]] = {
    "query": ("query", "name", "message", "smiles", "cid"),
    "smiles": ("smiles", "canonical_smiles"),
    "smiles_list": ("smiles_list", "molecules"),
    "reaction": ("reaction", "reaction_smiles"),
    "smarts": ("smarts", "substructure", "query_smarts"),
    "formula": ("formula", "target_formula"),
    "formulas": ("formulas", "formula_list", "candidates"),
    "space_group": ("space_group", "spacegroup", "sg", "space_group_number"),
    "structure_text": ("structure_text", "text", "cif", "poscar"),
    "structure_text_a": ("structure_text_a", "structure_a"),
    "structure_text_b": ("structure_text_b", "structure_b"),
    "observed_peaks": ("observed_peaks",),
    "reference_peaks": ("reference_peaks",),
    "x_values": ("x_values",),
    "y_values": ("y_values",),
    "xy_text": ("xy_text",),
    "target_formula": ("target_formula", "formula"),
    "target_mass_g": ("target_mass_g",),
    "precursors": ("precursors",),
    "elements": ("elements",),
    "value": ("value",),
    "from_unit": ("from_unit",),
    "to_unit": ("to_unit",),
    "peak_positions": ("peak_positions",),
    "material_id": ("material_id",),
    "material_ids": ("material_ids",),
    "chemical_system": ("chemical_system", "chemsys"),
}


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def _available_tool_specs(domain: str = "auto") -> list[JsonDict]:
    domain_key = str(domain or "auto").strip().lower()
    tools = [
        tool.public_spec()
        for tool in SCIENCE_TOOLS.values()
        if domain_key in {"", "auto"} or tool.domain == domain_key
    ]
    return tools


def _compact_tool_specs(domain: str = "auto") -> list[JsonDict]:
    return [
        {
            "key": spec["key"],
            "domain": spec["domain"],
            "description": spec["description"],
            "input_schema": spec["input_schema"],
        }
        for spec in _available_tool_specs(domain)
    ]


def _context_summary(context: JsonDict) -> JsonDict:
    summary: JsonDict = {}
    for key, value in sorted((context or {}).items()):
        if isinstance(value, str):
            summary[key] = {
                "type": "string",
                "length": len(value),
                "preview": value[:240],
            }
        elif isinstance(value, list):
            summary[key] = {
                "type": "list",
                "length": len(value),
                "preview": value[:5],
            }
        elif isinstance(value, dict):
            summary[key] = {
                "type": "object",
                "keys": sorted(str(item) for item in value.keys())[:20],
            }
        else:
            summary[key] = {"type": type(value).__name__, "value": value}
    return summary


_ELEMENT_SYMBOLS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
}
_FORMULA_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Z][a-z]?(?:\d+(?:\.\d+)?)?|\([A-Za-z0-9.]+\)\d*){1,}(?![A-Za-z0-9])"
)
_FORMULA_ELEMENT_RE = re.compile(r"[A-Z][a-z]?")
_NON_FORMULA_TOKENS = {"AI", "ML", "CIF", "POSCAR", "XYZ", "XRD", "FTIR", "UV", "IR", "GVIM"}


def _looks_like_formula_token(token: str) -> bool:
    cleaned = str(token or "").strip()
    if not cleaned or cleaned.upper() in _NON_FORMULA_TOKENS:
        return False
    if cleaned.isupper() and not any(char.isdigit() for char in cleaned) and len(cleaned) > 2:
        return False
    symbols = _FORMULA_ELEMENT_RE.findall(cleaned)
    if not symbols or any(symbol not in _ELEMENT_SYMBOLS for symbol in symbols):
        return False
    return any(char.isdigit() for char in cleaned) or len(symbols) >= 2 or len(cleaned) <= 3


def _coerce_context_formulas(value: Any) -> list[str]:
    if isinstance(value, str):
        items = value.replace(",", " ").replace(";", " ").split()
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        return []
    formulas: list[str] = []
    for item in items:
        formula = str(item or "").strip()
        if formula and formula not in formulas:
            formulas.append(formula)
    return formulas


def _extract_formula_candidates_from_message(message: str) -> list[str]:
    formulas: list[str] = []
    for match in _FORMULA_TOKEN_RE.finditer(str(message or "")):
        token = match.group(0).strip(".,;:，。；：()[]{}<>")
        if _looks_like_formula_token(token) and token not in formulas:
            formulas.append(token)
        if len(formulas) >= 50:
            break
    return formulas


def _is_batch_descriptor_request(message: str, formula_count: int) -> bool:
    text = str(message or "").lower()
    descriptor_terms = (
        "组成描述符",
        "composition descriptor",
        "composition descriptors",
        "magpie",
        "matminer",
        "feature vector",
        "features",
        "特征",
        "描述符",
    )
    table_terms = (
        "机器学习",
        "machine learning",
        "ml",
        "数据表",
        "table",
        "csv",
        "矩阵",
        "feature table",
    )
    return (
        formula_count >= 2
        and any(term in text for term in descriptor_terms)
        and any(term in text for term in table_terms)
    )


def _plan_deterministic_materials_batch_request(
    *,
    message: str,
    domain: str,
    context: JsonDict,
) -> tuple[JsonDict | None, JsonDict] | None:
    if domain not in {"", "auto", "materials"}:
        return None
    formulas: list[str] = []
    for key in ("formulas", "formula_list", "candidates"):
        formulas = _coerce_context_formulas(context.get(key))
        if formulas:
            break
    if not formulas:
        formulas = _extract_formula_candidates_from_message(message)
    if not _is_batch_descriptor_request(message, len(formulas)):
        return None
    return (
        {
            "domain": "materials",
            "tool_key": "composition_feature_table",
            "tool_args": {"formulas": formulas, "include_csv": True},
            "requires_input": False,
            "missing_fields": [],
            "reply": "",
            "confidence": 1.0,
        },
        {"provider": "deterministic", "model": "materials-batch-router"},
    )


def _plan_science_tool_with_llm(
    *,
    message: str,
    domain: str,
    context: JsonDict,
    mode: str,
) -> tuple[JsonDict | None, JsonDict]:
    parsed, settings = post_chemistry_llm_json(
        mode=mode,
        temperature=0.0,
        max_tokens=1200,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a scientific SaaS tool router for chemistry and materials. "
                    "Return strict JSON only with schema "
                    "{\"domain\":\"chemistry|materials\",\"tool_key\":\"\","
                    "\"tool_args\":{},\"requires_input\":false,\"missing_fields\":[],"
                    "\"reply\":\"\",\"confidence\":0.0}. "
                    "Choose exactly one whitelisted tool from available_tools. "
                    "The LLM only plans; Python tools compute the result. "
                    "Do not invent measurements, properties, structures, API results, or files. "
                    "If required data is present in context_summary, omit the bulky value or use "
                    "the same argument key with an empty value; the server will bind context. "
                    "If no tool is appropriate or required data is missing, set requires_input=true."
                ),
            },
            {
                "role": "user",
                "content": (
                    "available_tools="
                    f"{_compact_tool_specs(domain)}\n"
                    f"domain_hint={domain or 'auto'}\n"
                    f"context_summary={_context_summary(context)}\n"
                    f"user_message={message}"
                ),
            },
        ],
    )
    return parsed if isinstance(parsed, dict) else None, settings


def _sanitize_domain(value: Any) -> str:
    domain = str(value or "auto").strip().lower()
    return domain if domain in {"auto", "chemistry", "materials"} else "auto"


def _sanitize_plan(plan: Any, domain_hint: str) -> JsonDict | None:
    if not isinstance(plan, dict):
        return None
    tool_key = str(plan.get("tool_key") or plan.get("capability_key") or "").strip()
    if tool_key not in SCIENCE_TOOLS:
        return None
    tool = SCIENCE_TOOLS[tool_key]
    if domain_hint in {"chemistry", "materials"} and tool.domain != domain_hint:
        return None
    args = plan.get("tool_args")
    if not isinstance(args, dict):
        args = {}
    confidence = plan.get("confidence", 0.0)
    try:
        confidence_value = max(0.0, min(float(confidence), 1.0))
    except (TypeError, ValueError):
        confidence_value = 0.0
    missing_fields = plan.get("missing_fields")
    if not isinstance(missing_fields, list):
        missing_fields = []
    return {
        "domain": tool.domain,
        "tool_key": tool.key,
        "tool_args": deepcopy(args),
        "requires_input": bool(plan.get("requires_input", False)),
        "missing_fields": [str(item) for item in missing_fields if str(item).strip()],
        "reply": str(plan.get("reply") or "").strip(),
        "confidence": confidence_value,
    }


def _bind_context_args(tool: ScienceTool, args: JsonDict, context: JsonDict, message: str) -> JsonDict:
    bound = deepcopy(args) if isinstance(args, dict) else {}
    if tool.key == "chemistry_studio_prepare" and not _is_present(bound.get("query")):
        bound["query"] = message
    for required_key in sorted(set(tool.required) | {item for group in tool.required_any for item in group}):
        if _is_present(bound.get(required_key)):
            continue
        for alias in CONTEXT_ARG_ALIASES.get(required_key, (required_key,)):
            if _is_present(context.get(alias)):
                bound[required_key] = context.get(alias)
                break
    return bound


def _missing_required_args(tool: ScienceTool, args: JsonDict) -> list[str]:
    missing = [key for key in tool.required if not _is_present(args.get(key))]
    if tool.required_any:
        satisfied = any(all(_is_present(args.get(key)) for key in group) for group in tool.required_any)
        if not satisfied:
            missing.append(" or ".join(" + ".join(group) for group in tool.required_any))
    return missing


def _build_reply(message: str, plan: JsonDict, result: JsonDict) -> str:
    planned_reply = str(plan.get("reply") or "").strip()
    if planned_reply:
        return planned_reply
    if not result.get("success", False):
        return "The selected scientific tool could not complete the request."
    tool_key = plan.get("tool_key")
    if tool_key == "rdkit_reaction_qc":
        return "Reaction QC completed with RDKit balance and atom-map checks."
    if tool_key == "rdkit_substructure_search":
        return "SMARTS substructure search completed with RDKit."
    if tool_key == "structure_qc":
        return "Structure QC completed with lightweight parsing and geometry checks."
    if tool_key == "structure_transform":
        return "Structure conversion completed."
    if tool_key == "structure_description":
        return "Structure description completed with robocrys."
    if tool_key == "pyxtal_structure_generation":
        return "PyXtal candidate structure generation completed."
    if tool_key == "spectrum_peak_fit":
        return "Peak fitting completed with lmfit."
    return "Scientific tool execution completed."


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _ketcher_artifact_payload(result: JsonDict) -> JsonDict:
    current = result.get("current_structure")
    current_structure = current if isinstance(current, dict) else {}
    command = first_structure_command(result)
    payload = with_ketcher_commands(result)
    payload["smiles"] = _first_non_empty(
        result.get("smiles"),
        result.get("canonical_smiles"),
        current_structure.get("canonical_smiles"),
        current_structure.get("smiles"),
        command.get("smiles"),
        command.get("canonical_smiles"),
    )
    payload["molfile"] = _first_non_empty(
        result.get("molfile"),
        result.get("molblock"),
        current_structure.get("molfile"),
        current_structure.get("molblock"),
        command.get("molfile"),
        command.get("molblock"),
    )
    payload["rxnblock"] = _first_non_empty(
        result.get("rxnblock"),
        result.get("rxnfile"),
        command.get("rxnblock"),
        command.get("rxnfile"),
    )
    payload["ket"] = _first_non_empty(
        result.get("ket"),
        current_structure.get("ket"),
        command.get("ket"),
        command.get("value") if str(command.get("type") or "") == "load_ket" else "",
    )
    return payload


def _science_artifact_title(kind: str, tool_key: str, result: JsonDict) -> str:
    formula = _first_non_empty(
        result.get("reduced_formula"),
        result.get("formula"),
        result.get("formula_pretty"),
    )
    smiles = _first_non_empty(
        result.get("canonical_smiles"),
        result.get("smiles"),
    )
    if kind == "ketcher":
        return f"Ketcher: {smiles}" if smiles else "Ketcher structure"
    if kind == "three-d":
        label = formula or smiles
        return f"3D structure: {label}" if label else "3D structure"
    label = formula or tool_key
    return f"Materials: {label}" if label else "Materials result"


def _science_artifacts_for_result(tool_key: str, domain: str, result: Any) -> list[JsonDict]:
    """Declare native UI artifacts for GVIM science tool results.

    The frontend intentionally consumes this explicit contract instead of
    guessing from generic JSON keys such as ``results``.
    """
    if not isinstance(result, dict):
        return []

    current = result.get("current_structure")
    current_structure = current if isinstance(current, dict) else {}
    commands = ketcher_commands_from_payload(result)
    has_structure_command = any(
        isinstance(command, dict)
        and str(command.get("type") or "") in KETCHER_STRUCTURE_COMMAND_TYPES
        for command in commands
    )
    has_ketcher_payload = has_structure_command or any(
        current_structure.get(key)
        for key in ("smiles", "canonical_smiles", "molfile", "molblock")
    )
    has_3d_payload = (
        str(result.get("viewer") or "").lower() == "3dmol"
        or bool(result.get("pdb_block"))
        or (
            bool(result.get("molblock"))
            and "rdkit_native" in str(result.get("source") or "").lower()
        )
    )

    if has_3d_payload:
        return [
            {
                "kind": "three-d",
                "title": _science_artifact_title("three-d", tool_key, result),
                "tool_key": tool_key,
                "payload": result,
            }
        ]
    if has_ketcher_payload:
        payload = _ketcher_artifact_payload(result)
        return [
            {
                "kind": "ketcher",
                "title": _science_artifact_title("ketcher", tool_key, payload),
                "tool_key": tool_key,
                "payload": payload,
            }
        ]
    if domain == "materials":
        return [
            {
                "kind": "materials",
                "title": _science_artifact_title("materials", tool_key, result),
                "tool_key": tool_key,
                "payload": result,
            }
        ]
    return []


def build_science_capabilities_payload() -> JsonDict:
    chemistry_payload = build_chemistry_capabilities_payload()
    return {
        "version": "1.0",
        "product_surface": "science_copilot",
        "execution_model": "llm_tool_router_with_whitelisted_package_backends",
        "supported": _available_tool_specs("auto"),
        "domain_counts": {
            "chemistry": sum(1 for tool in SCIENCE_TOOLS.values() if tool.domain == "chemistry"),
            "materials": sum(1 for tool in SCIENCE_TOOLS.values() if tool.domain == "materials"),
        },
        "planner": {
            "provider_contract": "OpenAI-compatible JSON chat completion",
            "intent_source": "model_understanding",
            "execution_policy": "LLM returns tool_key/tool_args only; server executes whitelisted Python functions.",
        },
        "chemistry_contract": chemistry_payload.get("skill", {}).get("contract", {}),
        "deployment_limits": {
            "profile": "vps_lightweight",
            "single_tool_per_request": True,
            "composition_feature_table_max_formulas": 50,
            "composition_feature_table_max_features": 200,
            "large_model_or_dft_execution": False,
        },
    }


def build_science_execution_payload(
    message: Any,
    *,
    domain: Any = "auto",
    context: Any = None,
    mode: Any = "smart",
    execute: Any = True,
) -> tuple[JsonDict, int]:
    raw_message = str(message or "").strip()
    if not raw_message:
        return {"success": False, "error": "message is required"}, 400
    domain_hint = _sanitize_domain(domain)
    mode_name = str(mode or "smart").strip().lower()
    if mode_name not in {"smart", "deep"}:
        mode_name = "smart"
    context_dict = deepcopy(context) if isinstance(context, dict) else {}
    deterministic = _plan_deterministic_materials_batch_request(
        message=raw_message,
        domain=domain_hint,
        context=context_dict,
    )
    if deterministic:
        plan, settings = deterministic
    else:
        plan, settings = _plan_science_tool_with_llm(
            message=raw_message,
            domain=domain_hint,
            context=context_dict,
            mode=mode_name,
        )
    sanitized = _sanitize_plan(plan, domain_hint)
    if not sanitized:
        return {
            "success": False,
            "intent": "planner_unavailable",
            "error": "LLM tool planning is unavailable or returned an unsupported tool.",
            "planner_settings": {
                "provider": settings.get("provider"),
                "model": settings.get("model"),
            },
            "supported_tools": _available_tool_specs(domain_hint),
        }, 503
    if sanitized.get("requires_input"):
        return {
            "success": False,
            "intent": "requires_input",
            "plan": sanitized,
            "missing_fields": sanitized.get("missing_fields", []),
            "reply": sanitized.get("reply") or "More input is required to run this scientific tool.",
        }, 400

    tool = SCIENCE_TOOLS[sanitized["tool_key"]]
    bound_args = _bind_context_args(tool, sanitized.get("tool_args") or {}, context_dict, raw_message)
    missing = _missing_required_args(tool, bound_args)
    sanitized["tool_args"] = bound_args
    if missing:
        return {
            "success": False,
            "intent": "requires_input",
            "plan": sanitized,
            "missing_fields": missing,
            "reply": "The selected tool needs additional structured input.",
        }, 400
    if not bool(execute):
        return {
            "success": True,
            "executed": False,
            "message": raw_message,
            "plan": sanitized,
            "planner": {
                "provider": settings.get("provider"),
                "model": settings.get("model"),
            },
        }, 200

    try:
        tool_result = tool.runner(bound_args)
    except MaterialsDependencyError as exc:
        return {
            "success": False,
            "intent": "missing_dependency",
            "plan": sanitized,
            "error": str(exc),
            "missing_dependency": True,
        }, 503
    except ValueError as exc:
        return {
            "success": False,
            "intent": "tool_error",
            "plan": sanitized,
            "error": str(exc),
        }, 400
    except Exception as exc:
        return {
            "success": False,
            "intent": "tool_error",
            "plan": sanitized,
            "error": str(exc),
        }, 500

    science_artifacts = _science_artifacts_for_result(tool.key, tool.domain, tool_result)
    return {
        "success": bool(tool_result.get("success", True)),
        "version": "1.0",
        "product_surface": "science_copilot",
        "message": raw_message,
        "domain": tool.domain,
        "tool_key": tool.key,
        "plan": sanitized,
        "tool_result": tool_result,
        "science_artifacts": science_artifacts,
        "reply": _build_reply(raw_message, sanitized, tool_result),
        "planner": {
            "provider": settings.get("provider"),
            "model": settings.get("model"),
        },
        "observability": {
            "tool_source": tool_result.get("source"),
            "tool_engine": tool_result.get("engine"),
            "limitations": tool_result.get("limitations", []),
        },
    }, 200


__all__ = [
    "SCIENCE_TOOLS",
    "build_science_capabilities_payload",
    "build_science_execution_payload",
]
