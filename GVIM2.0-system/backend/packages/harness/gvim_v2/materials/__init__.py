"""Package-backed materials-science services for the v2 GVIM surface."""

from .errors import FormulaError, MaterialsDependencyError
from .advanced_analysis import (
    batch_composition_features,
    composition_features,
    convert_unit,
    correct_spectrum_baseline,
    detect_spectrum_peaks,
    element_properties,
    fit_spectrum_peaks,
    high_symmetry_kpath,
)
from .formula_analysis import analyze_formula, screen_formulas
from .materials_project import (
    materials_project_deep_profile,
    materials_project_profile,
    search_materials_project,
)
from .precursor_planning import plan_precursors
from .reference_data import (
    resolve_pubchem_compound,
    scattering_reference_data,
    search_optimade_structures,
    xray_reference_data,
)
from .structure_analysis import (
    analyze_local_environment,
    analyze_structure,
    match_structures,
    quality_check_structure,
    simulate_and_match_xrd,
    simulate_xrd,
    transform_structure,
)
from .structure_generation import (
    describe_structure_with_robocrys,
    generate_pyxtal_structures,
)
from .xrd_matching import match_xrd_peaks

__all__ = [
    "analyze_formula",
    "batch_composition_features",
    "composition_features",
    "convert_unit",
    "correct_spectrum_baseline",
    "detect_spectrum_peaks",
    "element_properties",
    "fit_spectrum_peaks",
    "high_symmetry_kpath",
    "screen_formulas",
    "FormulaError",
    "MaterialsDependencyError",
    "match_xrd_peaks",
    "materials_project_profile",
    "materials_project_deep_profile",
    "search_materials_project",
    "analyze_structure",
    "analyze_local_environment",
    "match_structures",
    "quality_check_structure",
    "simulate_xrd",
    "simulate_and_match_xrd",
    "transform_structure",
    "describe_structure_with_robocrys",
    "generate_pyxtal_structures",
    "plan_precursors",
    "resolve_pubchem_compound",
    "scattering_reference_data",
    "search_optimade_structures",
    "xray_reference_data",
]
