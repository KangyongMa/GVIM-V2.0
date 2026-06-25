---
name: materials-core
description: Package-backed materials science workflows for formulas, structures, XRD, precursor stoichiometry, units, spectra, local environments, and composition descriptors. Use when the user asks about inorganic/material formulas, CIF/POSCAR/XYZ structures, powder XRD, precursor planning, or lightweight materials screening.
allowed-tools:
  - gvim-science_gvim_science_capabilities
  - gvim-science_gvim_science_execute
  - gvim-science_gvim_science_run_tool
  - gvim-science_gvim_materials_formula_analyze
  - gvim-science_gvim_materials_formula_screen
  - gvim-science_gvim_materials_structure_analyze
  - gvim-science_gvim_materials_xrd_simulate
  - gvim-science_gvim_materials_xrd_match
  - gvim-science_gvim_materials_xrd_simulate_match
  - gvim-science_gvim_materials_precursor_plan
---

# Materials Core

Identify the representation first: formula, formula list, structure text,
observed XRD peaks, reference peaks, precursor list, or uploaded data.

## Workflow

1. Formula only: call `gvim-science_gvim_materials_formula_analyze`.
2. Multiple formulas or target application triage: call `gvim-science_gvim_materials_formula_screen`.
3. CIF/POSCAR/XYZ: call `gvim-science_gvim_materials_structure_analyze`; add XRD simulation if requested.
4. Observed and reference XRD peaks: call `gvim-science_gvim_materials_xrd_match`.
5. Structure plus observed XRD: call `gvim-science_gvim_materials_xrd_simulate_match`.
6. Precursor mass planning: call `gvim-science_gvim_materials_precursor_plan`.
7. For advanced whitelisted tools such as local environment, composition features, unit conversion, spectrum tools, or k-path, call `gvim-science_gvim_science_run_tool`.

## Evidence Rules

- Formula parsing is not phase stability, property, or application evidence.
- XRD matching is peak-position triage, not proof of phase purity.
- Precursor planning returns stoichiometry and masses, not a validated synthesis protocol.
- State missing dependencies or missing database evidence instead of approximating.
- Preserve returned `science_artifacts`, tables, peak lists, structure summaries, and quality flags so DeerFlow can render native materials artifacts without hardcoded response templates.
