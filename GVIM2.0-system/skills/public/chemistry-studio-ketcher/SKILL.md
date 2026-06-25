---
name: chemistry-studio-ketcher
description: Natural-language Chemistry Studio workflow for drawing molecules, reactions, retrosynthesis sketches, and route drafts in Ketcher. Use when the user asks to draw, load, sketch, edit, or prepare a molecule/reaction canvas, including Chinese names, common names, CAS-like text, SMILES, reaction SMILES, or route descriptions.
allowed-tools:
  - gvim-science_gvim_science_capabilities
  - gvim-science_gvim_science_execute
  - gvim-science_gvim_chemistry_prepare_studio
  - gvim-science_gvim_chemistry_resolve_structure
  - gvim-science_gvim_rdkit_reaction_qc
---

# Chemistry Studio Ketcher

Use Ketcher as the primary chemistry canvas. Treat natural language as the
source of intent; do not require SMILES unless structure resolution fails.

## Workflow

1. For molecule, reaction, or route drawing, call `gvim-science_gvim_chemistry_prepare_studio`.
2. Pass the user's original wording. For follow-ups, include active canvas context in the query when available.
3. If the result only opens Ketcher without a structure command (`load_molecule`, `load_reaction`, or `load_ket`) or a concrete structure payload (`smiles`, `molblock`, `rxnblock`, or `ket`), say that drawing was not completed and ask for a clearer name, CAS number, English name, or SMILES.
4. If the user gives reaction SMILES, call `gvim-science_gvim_rdkit_reaction_qc` when balance or validity matters.
5. Keep the final answer short for canvas-only requests: state what was loaded and include canonical SMILES or reaction SMILES if returned.

## Native DeerFlow Artifact Contract

- Let DeerFlow decide tool use from the user's intent; do not emulate Ketcher behavior with preset text templates.
- Preserve returned `science_artifacts`, `ketcher_commands`, `current_structure`, `molfile`, `rxnblock`, `ket`, and `smiles` fields so the native frontend can render and control Ketcher directly.
- Use explicit `ketcher_commands` for verified native editor operations such as `add_text`, `layout`, `set_zoom`, `set_settings`, `switch_mode`, and `clear`; do not describe these operations only in prose when the user asked the canvas to change.
- Do not summarize away structured editor payloads when the user asked for a drawable/editable structure.

## Boundaries

- Do not claim that the molecule was loaded unless the tool returns a concrete KetcherCommand.
- Do not invent mechanisms, yields, conditions, spectra, ADMET, or safety conclusions.
- Treat route drawings as planning drafts, not validated synthesis routes.
- Preserve stereochemistry, salts, charges, isotope labels, and atom mapping when the tool returns them.
