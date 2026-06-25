---
name: rdkit-molecular-analysis
description: RDKit-backed molecular analysis for descriptors, similarity, standardization, scaffolds, fragments, substructure checks, reaction QC, and 3D conformer generation. Use for cheminformatics calculations after molecule structures are available or resolved.
allowed-tools:
  - gvim-science_gvim_science_capabilities
  - gvim-science_gvim_science_run_tool
  - gvim-science_gvim_chemistry_resolve_structure
  - gvim-science_gvim_rdkit_descriptors
  - gvim-science_gvim_rdkit_similarity
  - gvim-science_gvim_rdkit_reaction_qc
  - gvim-science_gvim_rdkit_standardize
  - gvim-science_gvim_rdkit_fragments
  - gvim-science_gvim_rdkit_conformer
---

# RDKit Molecular Analysis

Use this Skill only for real RDKit-backed cheminformatics. Resolve names first
when the user does not provide validated SMILES.

## Tool Selection

- Descriptors: `gvim-science_gvim_rdkit_descriptors`
- Similarity: `gvim-science_gvim_rdkit_similarity`
- Reaction balance or atom-map checks: `gvim-science_gvim_rdkit_reaction_qc`
- Cleanup, parent, uncharge, tautomer handling: `gvim-science_gvim_rdkit_standardize`
- Murcko scaffold or BRICS fragments: `gvim-science_gvim_rdkit_fragments`
- Lightweight 3D conformer payload: `gvim-science_gvim_rdkit_conformer`
- Less common whitelisted tools: `gvim-science_gvim_science_run_tool`

## Response Rules

- Report RDKit values as computed descriptors, not experimental facts.
- State invalid SMILES or dependency failures directly.
- Do not claim ADMET, docking, binding affinity, spectra, pharmacology, or lab safety unless a real tool returns that evidence.
- For similarity, identify the fingerprint and metric returned by the tool.
- Preserve returned `science_artifacts`, `viewer`, `molblock`, and `pdb_block` fields so DeerFlow can render native 3D artifacts instead of turning structures into plain text.
