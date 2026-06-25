"""Lightweight RDKit reaction and substructure utilities for v2 chemistry."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Tuple

from rdkit import Chem, RDLogger
from rdkit.Chem import rdChemReactions, rdMolDescriptors


RDLogger.DisableLog("rdApp.error")

MAX_SUBSTRUCTURE_MOLECULES = 200


def _mol_from_smiles(smiles: Any) -> Chem.Mol:
    cleaned = str(smiles or "").strip()
    if not cleaned:
        raise ValueError("SMILES string is required")
    mol = Chem.MolFromSmiles(cleaned)
    if mol is None:
        raise ValueError(f"Invalid SMILES string: {cleaned}")
    return mol


def _canonical_smiles(smiles: Any) -> str:
    mol = _mol_from_smiles(smiles)
    return Chem.MolToSmiles(mol, canonical=True)


def _split_reaction_smiles(reaction: Any) -> tuple[list[str], list[str]]:
    normalized = str(reaction or "").strip().replace("->", ">>").replace("=>", ">>")
    normalized = normalized.replace("\u2192", ">>")
    if ">>" not in normalized:
        raise ValueError("reaction must contain >>, ->, =>, or -> between reactants and products")
    left, right = normalized.split(">>", 1)
    reactants = [item.strip() for item in left.split(".") if item.strip()]
    products = [item.strip() for item in right.split(".") if item.strip()]
    if not reactants or not products:
        raise ValueError("reaction must include at least one reactant and one product")
    return reactants, products


def _component_payload(smiles: str, role: str, index: int) -> dict[str, Any]:
    mol = _mol_from_smiles(smiles)
    formula = rdMolDescriptors.CalcMolFormula(mol)
    charge = int(sum(atom.GetFormalCharge() for atom in mol.GetAtoms()))
    mapped_atoms = [
        int(atom.GetAtomMapNum())
        for atom in mol.GetAtoms()
        if int(atom.GetAtomMapNum() or 0) > 0
    ]
    element_counts: Counter[str] = Counter()
    for atom in mol.GetAtoms():
        element_counts[atom.GetSymbol()] += 1
        hydrogen_count = int(atom.GetTotalNumHs())
        if hydrogen_count:
            element_counts["H"] += hydrogen_count
    return {
        "role": role,
        "index": index,
        "input_smiles": smiles,
        "canonical_smiles": Chem.MolToSmiles(mol, canonical=True),
        "molecular_formula": formula,
        "formal_charge": charge,
        "heavy_atom_count": int(mol.GetNumHeavyAtoms()),
        "atom_count_with_implicit_h": int(sum(element_counts.values())),
        "element_counts": dict(sorted(element_counts.items())),
        "mapped_atom_count": len(mapped_atoms),
        "atom_map_numbers": sorted(set(mapped_atoms)),
    }


def _sum_element_counts(components: list[dict[str, Any]]) -> Counter[str]:
    total: Counter[str] = Counter()
    for component in components:
        total.update(component.get("element_counts") or {})
    return total


def _reaction_to_rxnblock(reaction_smiles: str) -> str:
    try:
        reaction = rdChemReactions.ReactionFromSmarts(reaction_smiles, useSmiles=True)
        if reaction is None:
            return ""
        return rdChemReactions.ReactionToRxnBlock(reaction)
    except Exception:
        return ""


def build_reaction_qc_payload(reaction: Any) -> Dict[str, Any]:
    """Check reaction balance, charges, and atom-map coverage from reaction SMILES."""
    reactant_smiles, product_smiles = _split_reaction_smiles(reaction)
    reactants = [
        _component_payload(smiles, "reactant", index)
        for index, smiles in enumerate(reactant_smiles)
    ]
    products = [
        _component_payload(smiles, "product", index)
        for index, smiles in enumerate(product_smiles)
    ]
    canonical_reaction = (
        ".".join(item["canonical_smiles"] for item in reactants)
        + ">>"
        + ".".join(item["canonical_smiles"] for item in products)
    )
    reactant_elements = _sum_element_counts(reactants)
    product_elements = _sum_element_counts(products)
    all_elements = sorted(set(reactant_elements) | set(product_elements))
    element_balance = [
        {
            "element": element,
            "reactants": int(reactant_elements.get(element, 0)),
            "products": int(product_elements.get(element, 0)),
            "delta_products_minus_reactants": int(
                product_elements.get(element, 0) - reactant_elements.get(element, 0)
            ),
            "balanced": reactant_elements.get(element, 0) == product_elements.get(element, 0),
        }
        for element in all_elements
    ]
    reactant_charge = int(sum(item["formal_charge"] for item in reactants))
    product_charge = int(sum(item["formal_charge"] for item in products))
    reactant_maps = sorted(
        {
            number
            for component in reactants
            for number in component.get("atom_map_numbers", [])
        }
    )
    product_maps = sorted(
        {
            number
            for component in products
            for number in component.get("atom_map_numbers", [])
        }
    )
    heavy_reactant_atoms = sum(item["heavy_atom_count"] for item in reactants)
    heavy_product_atoms = sum(item["heavy_atom_count"] for item in products)
    mapped_reactant_atoms = sum(item["mapped_atom_count"] for item in reactants)
    mapped_product_atoms = sum(item["mapped_atom_count"] for item in products)
    issues: list[dict[str, str]] = []
    if any(not item["balanced"] for item in element_balance):
        issues.append(
            {
                "severity": "warning",
                "code": "element_imbalance",
                "message": "Reactant and product element counts are not balanced.",
            }
        )
    if reactant_charge != product_charge:
        issues.append(
            {
                "severity": "warning",
                "code": "charge_imbalance",
                "message": "Reactant and product total formal charges differ.",
            }
        )
    missing_product_maps = sorted(set(reactant_maps) - set(product_maps))
    missing_reactant_maps = sorted(set(product_maps) - set(reactant_maps))
    if missing_product_maps or missing_reactant_maps:
        issues.append(
            {
                "severity": "warning",
                "code": "atom_map_mismatch",
                "message": "Atom-map numbers are not present on both sides of the reaction.",
            }
        )

    return {
        "success": True,
        "version": "1.0",
        "source": "rdkit_reaction_qc",
        "engine": "rdkit",
        "input_reaction": str(reaction or "").strip(),
        "canonical_reaction_smiles": canonical_reaction,
        "rxnblock": _reaction_to_rxnblock(canonical_reaction),
        "balanced_elements": all(item["balanced"] for item in element_balance),
        "charge_balanced": reactant_charge == product_charge,
        "reactant_total_charge": reactant_charge,
        "product_total_charge": product_charge,
        "element_balance": element_balance,
        "reactants": reactants,
        "products": products,
        "atom_mapping": {
            "reactant_mapped_atoms": mapped_reactant_atoms,
            "product_mapped_atoms": mapped_product_atoms,
            "reactant_heavy_atoms": heavy_reactant_atoms,
            "product_heavy_atoms": heavy_product_atoms,
            "reactant_coverage": round(mapped_reactant_atoms / heavy_reactant_atoms, 4)
            if heavy_reactant_atoms
            else 0.0,
            "product_coverage": round(mapped_product_atoms / heavy_product_atoms, 4)
            if heavy_product_atoms
            else 0.0,
            "reactant_map_numbers": reactant_maps,
            "product_map_numbers": product_maps,
            "shared_map_numbers": sorted(set(reactant_maps) & set(product_maps)),
            "missing_on_products": missing_product_maps,
            "missing_on_reactants": missing_reactant_maps,
        },
        "issue_count": len(issues),
        "issues": issues,
        "limitations": [
            "Reaction QC checks formula, charge, and atom-map consistency only; it does not prove mechanism, yield, selectivity, or experimental feasibility.",
            "Implicit hydrogen handling follows RDKit sanitization for each component SMILES.",
        ],
    }


def analyze_reaction_qc(reaction: Any) -> Tuple[Dict[str, Any], int]:
    try:
        return build_reaction_qc_payload(reaction), 200
    except ValueError as exc:
        return {"success": False, "error": str(exc)}, 400
    except Exception as exc:
        return {"success": False, "error": str(exc)}, 500


def build_substructure_search_payload(
    smiles_list: Any,
    smarts: Any,
    labels: Any = None,
    max_matches_per_molecule: Any = 20,
) -> Dict[str, Any]:
    """Search a molecule list for a SMARTS query with RDKit."""
    if not isinstance(smiles_list, list) or not smiles_list:
        raise ValueError("smiles_list must be a non-empty list")
    if len(smiles_list) > MAX_SUBSTRUCTURE_MOLECULES:
        raise ValueError(f"substructure search is limited to {MAX_SUBSTRUCTURE_MOLECULES} molecules")
    query_smarts = str(smarts or "").strip()
    if not query_smarts:
        raise ValueError("smarts is required")
    query = Chem.MolFromSmarts(query_smarts)
    if query is None:
        raise ValueError("Invalid SMARTS query")
    if labels is not None and not isinstance(labels, list):
        raise ValueError("labels must be a list when provided")
    try:
        match_limit = max(1, min(int(max_matches_per_molecule or 20), 100))
    except (TypeError, ValueError) as exc:
        raise ValueError("max_matches_per_molecule must be an integer") from exc

    molecules: list[dict[str, Any]] = []
    matched_count = 0
    for index, raw_smiles in enumerate(smiles_list):
        smiles = str(raw_smiles or "").strip()
        label = str(labels[index]) if isinstance(labels, list) and index < len(labels) else f"molecule_{index}"
        mol = _mol_from_smiles(smiles)
        matches = [list(match) for match in mol.GetSubstructMatches(query, uniquify=True)]
        if matches:
            matched_count += 1
        molecules.append(
            {
                "index": index,
                "label": label,
                "input_smiles": smiles,
                "canonical_smiles": Chem.MolToSmiles(mol, canonical=True),
                "matched": bool(matches),
                "match_count": len(matches),
                "matches": matches[:match_limit],
                "matches_truncated": len(matches) > match_limit,
            }
        )

    return {
        "success": True,
        "version": "1.0",
        "source": "rdkit_substructure_search",
        "engine": "rdkit",
        "query": {
            "smarts": query_smarts,
            "query_atom_count": int(query.GetNumAtoms()),
        },
        "molecule_count": len(molecules),
        "matched_molecule_count": matched_count,
        "unmatched_molecule_count": len(molecules) - matched_count,
        "molecules": molecules,
        "limitations": [
            "SMARTS matching is a graph query on the supplied structures and depends on protonation, aromaticity, tautomer, and standardization choices.",
        ],
    }


def search_substructure(
    smiles_list: Any,
    smarts: Any,
    labels: Any = None,
    max_matches_per_molecule: Any = 20,
) -> Tuple[Dict[str, Any], int]:
    try:
        return (
            build_substructure_search_payload(
                smiles_list,
                smarts,
                labels=labels,
                max_matches_per_molecule=max_matches_per_molecule,
            ),
            200,
        )
    except ValueError as exc:
        return {"success": False, "error": str(exc)}, 400
    except Exception as exc:
        return {"success": False, "error": str(exc)}, 500


__all__ = [
    "analyze_reaction_qc",
    "build_reaction_qc_payload",
    "build_substructure_search_payload",
    "search_substructure",
]
