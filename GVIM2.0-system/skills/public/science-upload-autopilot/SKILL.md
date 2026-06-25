---
name: science-upload-autopilot
description: Auto-route uploaded or pasted chemistry/materials data such as CIF, POSCAR, XYZ, CSV formula tables, SMILES lists, XRD peak tables, and XY spectra through GVIM science tools, then summarize executed steps and evidence gaps.
allowed-tools:
  - gvim-science_gvim_science_capabilities
  - gvim-science_gvim_science_uploaded_data_autopilot
  - gvim-science_gvim_science_run_tool
  - gvim-science_gvim_materials_structure_analyze
  - gvim-science_gvim_materials_xrd_simulate
  - gvim-science_gvim_materials_xrd_match
  - gvim-science_gvim_rdkit_descriptors
  - gvim-science_gvim_rdkit_similarity
---

# Science Upload Autopilot

Use this Skill first when the user uploads or pastes scientific data and asks
for chemistry or materials analysis.

## Workflow

1. Call `gvim-science_gvim_science_uploaded_data_autopilot` with filename, extracted text, user goal, and optional target application.
2. Use `executed_steps` as the evidence source for the answer.
3. If the autopilot only extracts peaks or candidates, ask for the missing reference data, structure, or target question.
4. Use `gvim-science_gvim_science_run_tool` for a follow-up deterministic tool when the user's next question narrows the goal.

## Response Rules

- Summarize detected data types and successful steps first.
- Include key numerical results only if returned by tools.
- State evidence gaps explicitly.
- Do not infer phase purity, stability, band gap, ADMET, spectra, or synthesis feasibility from uploaded text alone.
- Preserve returned `science_artifacts`, executed step payloads, parsed structures, peaks, and tables so DeerFlow can render native chemistry/materials artifacts from the actual tool output.
