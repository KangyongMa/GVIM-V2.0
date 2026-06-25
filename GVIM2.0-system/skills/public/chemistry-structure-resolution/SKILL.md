---
name: chemistry-structure-resolution
description: Resolve chemical names, Chinese compound names, IUPAC names, common names, CAS-like identifiers, PubChem identifiers, SMILES, InChI, and ambiguous molecule descriptions into validated structure data before chemistry analysis or Ketcher drawing.
allowed-tools:
  - gvim-science_gvim_science_capabilities
  - gvim-science_gvim_chemistry_resolve_structure
  - gvim-science_gvim_chemistry_prepare_studio
  - gvim-science_gvim_rdkit_descriptors
  - gvim-science_gvim_rdkit_standardize
---

# Chemistry Structure Resolution

Resolve names before running RDKit tools when the input is not already a clear
SMILES, reaction SMILES, SMARTS, molblock, or rxnblock.

## Workflow

1. Call `gvim-science_gvim_chemistry_resolve_structure` with the original user query.
2. Prefer validated canonical SMILES from the tool result over model-generated SMILES.
3. If multiple candidates or conflicts appear, present the candidates and ask the user to choose.
4. After successful resolution, use the canonical structure for Ketcher loading or RDKit analysis.
5. When resolution fails, ask for an English name, CAS number, PubChem CID, or SMILES.

## Evidence Rules

- Separate resolved identifiers, PubChem records, and RDKit-derived values.
- Do not convert an uncertain natural-language description into a confident structure.
- Do not infer biological activity, toxicity, spectra, or synthesis feasibility from structure resolution alone.
- Preserve canonical structure fields returned by tools so downstream DeerFlow tools and native artifacts can reuse them without re-resolving or guessing.
