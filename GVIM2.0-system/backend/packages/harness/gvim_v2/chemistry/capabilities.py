"""Skill-first chemistry capability registry.

This module is the single source of truth for the public Chemistry Studio
surface. Natural-language understanding belongs to the LLM planner; RDKit is
used for deterministic validation and computation after the model has selected
the intended capability.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from gvim_v2.chemistry.ketcher_commands import KETCHER_COMMANDS

CHEMISTRY_SKILL_ID = "chemistry-studio"
CHEMISTRY_SKILL_VERSION = "2.2.0"
CHEMISTRY_EXECUTION_MODEL = "skill_driven_llm_planner_with_rdkit_validation"


_CAPABILITIES: list[dict[str, Any]] = [
    {
        "key": "chemistry_studio_prepare",
        "path": "/api/v2/chemistry/studio/prepare",
        "description": (
            "Understand natural-language molecule, reaction, or synthesis-route "
            "drawing requests and return canonical KetcherCommand objects."
        ),
        "source": "llm_planner_rdkit_validated",
        "natural_language": True,
        "execution": "llm_intent_plan_then_validated_ketcher_commands",
        "schema": {
            "input": {
                "query": "natural-language drawing request",
                "allow_pubchem": "optional boolean",
            },
            "output": {
                "ketcher_commands": "ordered canonical KetcherCommand objects",
                "current_structure": "validated molecule or route product summary",
                "route_state": "optional synthesis-route navigation state",
                "annotations": "optional short canvas labels such as non-operational reaction conditions",
            },
            "ketcher_commands": deepcopy(KETCHER_COMMANDS),
        },
        "safety": "No operational synthesis conditions are generated for canvas-only requests.",
    },
    {
        "key": "structure_resolver",
        "path": "/api/v2/chemistry/resolve",
        "description": (
            "Resolve direct SMILES or LLM-understood compound names to canonical "
            "RDKit structures, with optional PubChem and OPSIN verification."
        ),
        "source": "llm_resolver_rdkit_name_to_structure_optional",
        "natural_language": True,
        "execution": "llm_name_resolution_then_rdkit_canonicalization",
        "schema": {
            "input": {
                "query": "compound name, Chinese common name, CAS, SMILES, or structure text",
                "allow_pubchem": "optional boolean",
            },
            "output": {
                "canonical_smiles": "RDKit-canonical SMILES",
                "molecular_formula": "formula",
                "molecular_weight": "exact molecular weight",
            },
        },
    },
    {
        "key": "rdkit_descriptors",
        "path": "/api/v2/chemistry/rdkit/descriptors",
        "description": (
            "Compute RDKit-native numerical molecular descriptors for a "
            "validated SMILES string. The payload contains descriptor values "
            "computed directly by RDKit."
        ),
        "source": "rdkit_native",
        "natural_language": True,
        "execution": "natural_language_tool_selection_then_rdkit_descriptor_calculation",
        "schema": {
            "input": {"smiles": "validated SMILES"},
            "output": {"descriptors": "numeric RDKit descriptors"},
        },
    },
    {
        "key": "rdkit_3d_conformer",
        "path": "/api/v2/chemistry/rdkit/conformer",
        "description": (
            "Generate a browser-ready RDKit ETKDG 3D conformer with MMFF/UFF "
            "optimization for a validated SMILES string."
        ),
        "source": "rdkit_native",
        "natural_language": True,
        "execution": "natural_language_tool_selection_then_rdkit_3d_generation",
        "schema": {
            "input": {"smiles": "validated SMILES", "num_conformers": "1-30"},
            "output": {"molblock": "3D MolBlock", "energy": "force-field energy when available"},
        },
    },
    {
        "key": "rdkit_similarity",
        "path": "/api/v2/chemistry/rdkit/similarity",
        "description": (
            "Compare two to eight molecules with RDKit Morgan fingerprints and "
            "Tanimoto similarity."
        ),
        "source": "rdkit_native",
        "natural_language": True,
        "execution": "natural_language_tool_selection_then_fingerprint_similarity",
        "schema": {
            "input": {"smiles_list": "2-8 validated SMILES strings", "radius": "1-4"},
            "output": {"similarity_matrix": "pairwise Tanimoto scores"},
        },
    },
    {
        "key": "rdkit_reaction_qc",
        "path": "/api/v2/chemistry/rdkit/reaction-qc",
        "description": (
            "Check reaction SMILES for element balance, formal-charge balance, "
            "component formulas, and atom-map coverage."
        ),
        "source": "rdkit_native",
        "natural_language": True,
        "execution": "natural_language_tool_selection_then_rdkit_reaction_qc",
        "schema": {
            "input": {"reaction": "validated reaction SMILES"},
            "output": {
                "balanced_elements": "boolean",
                "charge_balanced": "boolean",
                "atom_mapping": "atom-map coverage and mismatches",
            },
        },
        "safety": "QC output is a structural consistency check, not a reaction feasibility or yield prediction.",
    },
    {
        "key": "rdkit_substructure_search",
        "path": "/api/v2/chemistry/rdkit/substructure",
        "description": (
            "Search a small molecule set with a SMARTS query and return matched "
            "atom indices for visualization or filtering."
        ),
        "source": "rdkit_native",
        "natural_language": True,
        "execution": "natural_language_tool_selection_then_smarts_search",
        "schema": {
            "input": {"smiles_list": "validated SMILES strings", "smarts": "SMARTS query"},
            "output": {"molecules": "per-molecule match counts and atom index matches"},
        },
    },
    {
        "key": "rdkit_standardization",
        "path": "/api/v2/chemistry/rdkit/standardize",
        "description": (
            "Run RDKit MolStandardize cleanup, fragment parent selection, "
            "uncharging, and canonical tautomer generation."
        ),
        "source": "rdkit_native",
        "natural_language": True,
        "execution": "natural_language_tool_selection_then_rdkit_standardization",
        "schema": {
            "input": {"smiles": "validated SMILES"},
            "output": {"standardized_smiles": "canonical standardized structure"},
        },
    },
    {
        "key": "rdkit_fragmentation",
        "path": "/api/v2/chemistry/rdkit/fragments",
        "description": (
            "Extract Murcko scaffold and BRICS fragments for structure triage "
            "from a validated SMILES string."
        ),
        "source": "rdkit_native",
        "natural_language": True,
        "execution": "natural_language_tool_selection_then_rdkit_fragmentation",
        "schema": {
            "input": {"smiles": "validated SMILES"},
            "output": {"murcko_scaffold": "core scaffold", "brics_fragments": "fragments"},
        },
    },
]


def build_chemistry_capabilities_payload() -> dict[str, Any]:
    """Return the public skill contract consumed by frontend and agents."""
    return {
        "version": "2.2",
        "product_surface": "chemistry_copilot",
        "execution_model": CHEMISTRY_EXECUTION_MODEL,
        "skill": {
            "id": CHEMISTRY_SKILL_ID,
            "name": "Chemistry Studio",
            "version": CHEMISTRY_SKILL_VERSION,
            "description": (
                "Natural-language control for Ketcher canvas drawing and RDKit "
                "analysis, driven by an LLM planner and validated with chemistry libraries."
            ),
            "manifest_paths": [
                "skills/public/chemistry-studio-ketcher/SKILL.md",
            ],
            "contract": {
                "intent_source": "model_understanding",
                "routing_policy": "llm_planner_with_deterministic_structured_input_guards",
                "validation": [
                    "explicit_reaction_smiles_preservation",
                    "local_curated_alias_lookup",
                    "rdkit_structure_parse",
                    "reaction_smiles_parse",
                    "drawable_reaction_component_evidence_gate",
                    "generated_reaction_single_atom_element_guard",
                    "stale_context_reaction_seed_rejection",
                    "optional_pubchem_lookup",
                    "optional_opsin_lookup",
                    "llm_smiles_identity_cross_check",
                ],
                "observability": ["capability_key", "source", "analysis", "warnings"],
                "ketcher_commands": deepcopy(KETCHER_COMMANDS),
            },
        },
        "supported": deepcopy(_CAPABILITIES),
        "unsupported": [
            {
                "key": "arbitrary_low_level_ketcher_ui_clicks",
                "description": (
                    "Unschematized toolbar clicks are not treated as agent actions. Ketcher "
                    "operations must be exposed as explicit KetcherCommand objects with validated payloads."
                ),
            },
            {
                "key": "experimental_synthesis_protocols",
                "description": (
                    "Canvas route drawings are structural drafts, not validated lab procedures."
                ),
            },
        ],
        "guarantees": [
            "Natural-language chemistry drawing requests go through the LLM planner.",
            "Explicit user-provided reaction SMILES are preserved and validated before any LLM planning.",
            "Common high-confidence aliases are resolved locally before LLM or network lookup.",
            "The service does not use legacy keyword templates for molecule or route drawing.",
            "LLM-generated reaction and synthesis-route drawings must pass the same component-evidence contract before Ketcher receives a seed.",
            "Ketcher canvas manipulation is represented as canonical KetcherCommand objects instead of browser-coordinate clicks.",
            "RDKit operations are exposed as natural-language selectable skill tools, while calculations remain deterministic.",
        ],
    }


__all__ = [
    "CHEMISTRY_EXECUTION_MODEL",
    "CHEMISTRY_SKILL_ID",
    "CHEMISTRY_SKILL_VERSION",
    "build_chemistry_capabilities_payload",
]
