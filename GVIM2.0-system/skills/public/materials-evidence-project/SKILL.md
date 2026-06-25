---
name: materials-evidence-project
description: Evidence-first materials database workflow for Materials Project, OPTIMADE, PubChem reference records, X-ray references, scattering references, stability, band gaps, formation energies, and database-backed materials claims.
allowed-tools:
  - gvim-science_gvim_science_capabilities
  - gvim-science_gvim_science_run_tool
  - gvim-science_gvim_materials_project_search
  - gvim-science_gvim_materials_project_profile
  - gvim-science_gvim_materials_project_deep_profile
  - gvim-science_gvim_materials_formula_analyze
---

# Materials Evidence Project

Use database tools whenever the user asks for stability, band gap, formation
energy, energy above hull, dielectric properties, DOS, band structure, elastic
data, Materials Project IDs, or database-backed comparisons.

## Workflow

1. Search candidates with `gvim-science_gvim_materials_project_search` when the material ID is unknown.
2. Use `gvim-science_gvim_materials_project_profile` for compact evidence on one material.
3. Use `gvim-science_gvim_materials_project_deep_profile` when the user asks for DOS, band structure, dielectric, elastic, thermo, or detailed database evidence.
4. Use `gvim-science_gvim_science_run_tool` for OPTIMADE, PubChem, X-ray, scattering, element-property, or composition-feature tools.

## Evidence Rules

- Report only values returned by the tools.
- Cite whether a value is database-computed, reference data, deterministic calculation, or model inference.
- If `MP_API_KEY` is missing or a record is unavailable, say so and do not invent values.
- Do not upgrade formula-only descriptors into stability, performance, or synthesis claims.
- Preserve returned `science_artifacts`, Materials Project IDs, source fields, and structured evidence arrays so the frontend can render database-backed materials artifacts natively.
