"""RDKit-native structure normalization and decomposition utilities."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from rdkit import Chem, RDLogger
from rdkit.Chem import BRICS, Descriptors, rdDepictor, rdMolDescriptors
from rdkit.Chem.Scaffolds import MurckoScaffold


RDLogger.DisableLog("rdApp.error")


def _mol_from_smiles(smiles: Any) -> tuple[str, Chem.Mol]:
    normalized_smiles = str(smiles or "").strip()
    if not normalized_smiles:
        raise ValueError("SMILES string is required")

    mol = Chem.MolFromSmiles(normalized_smiles)
    if mol is None:
        raise ValueError("Invalid SMILES string")

    return normalized_smiles, mol


def _molblock(mol: Chem.Mol | None) -> str:
    if mol is None or mol.GetNumAtoms() == 0:
        return ""

    copy = Chem.Mol(mol)
    try:
        rdDepictor.Compute2DCoords(copy)
    except Exception:
        return ""
    return Chem.MolToMolBlock(copy)


def _summary_from_mol(mol: Chem.Mol) -> dict[str, Any]:
    return {
        "canonical_smiles": Chem.MolToSmiles(mol, canonical=True),
        "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight": round(float(Descriptors.ExactMolWt(mol)), 4),
        "heavy_atom_count": int(mol.GetNumAtoms()),
        "bond_count": int(mol.GetNumBonds()),
    }


def build_standardization_payload(smiles: Any) -> Dict[str, Any]:
    """Run the RDKit MolStandardize workflow for one molecule."""
    input_smiles, mol = _mol_from_smiles(smiles)
    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    warnings: list[str] = []

    try:
        from rdkit.Chem.MolStandardize import rdMolStandardize
    except Exception as exc:  # pragma: no cover - depends on RDKit build
        raise ValueError(f"RDKit MolStandardize is unavailable: {exc}") from exc

    cleaned = rdMolStandardize.Cleanup(mol)
    fragment_parent = rdMolStandardize.FragmentParent(cleaned)
    uncharged = rdMolStandardize.Uncharger().uncharge(fragment_parent)
    canonical_tautomer = rdMolStandardize.TautomerEnumerator().Canonicalize(
        uncharged,
    )

    cleanup_smiles = Chem.MolToSmiles(cleaned, canonical=True)
    fragment_parent_smiles = Chem.MolToSmiles(fragment_parent, canonical=True)
    uncharged_smiles = Chem.MolToSmiles(uncharged, canonical=True)
    canonical_tautomer_smiles = Chem.MolToSmiles(
        canonical_tautomer,
        canonical=True,
    )

    if "." in canonical_smiles and "." not in fragment_parent_smiles:
        warnings.append("Disconnected fragments were reduced to a fragment parent.")
    if canonical_tautomer_smiles != canonical_smiles:
        warnings.append(
            "Canonical tautomer differs from the input canonical SMILES; verify chemistry context before replacing a drawn structure.",
        )

    return {
        "success": True,
        "version": "2.0",
        "source": "rdkit_native",
        "input_smiles": input_smiles,
        "canonical_smiles": canonical_smiles,
        "cleanup_smiles": cleanup_smiles,
        "fragment_parent_smiles": fragment_parent_smiles,
        "uncharged_smiles": uncharged_smiles,
        "canonical_tautomer_smiles": canonical_tautomer_smiles,
        "canonical_tautomer_molblock": _molblock(canonical_tautomer),
        "changed": {
            "cleanup": cleanup_smiles != canonical_smiles,
            "fragment_parent": fragment_parent_smiles != cleanup_smiles,
            "uncharged": uncharged_smiles != fragment_parent_smiles,
            "canonical_tautomer": canonical_tautomer_smiles != uncharged_smiles,
        },
        "structure": _summary_from_mol(canonical_tautomer),
        "warnings": warnings,
    }


def standardize_molecule(smiles: Any) -> Tuple[Dict[str, Any], int]:
    """Return a Flask-ready `(payload, status_code)` tuple."""
    try:
        return build_standardization_payload(smiles), 200
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except Exception as exc:
        return {"error": str(exc)}, 500


def build_fragmentation_payload(smiles: Any) -> Dict[str, Any]:
    """Extract Murcko scaffold and BRICS fragments for one molecule."""
    input_smiles, mol = _mol_from_smiles(smiles)
    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)

    scaffold = MurckoScaffold.GetScaffoldForMol(mol)
    scaffold_smiles = ""
    scaffold_molblock = ""
    generic_scaffold_smiles = ""
    if scaffold is not None and scaffold.GetNumAtoms() > 0:
        scaffold_smiles = Chem.MolToSmiles(scaffold, canonical=True)
        scaffold_molblock = _molblock(scaffold)
        generic_scaffold = MurckoScaffold.MakeScaffoldGeneric(scaffold)
        if generic_scaffold is not None and generic_scaffold.GetNumAtoms() > 0:
            generic_scaffold_smiles = Chem.MolToSmiles(
                generic_scaffold,
                canonical=True,
            )

    fragments = sorted(BRICS.BRICSDecompose(mol))
    warnings: list[str] = []
    if not scaffold_smiles:
        warnings.append("No Murcko scaffold was found for this molecule.")
    if not fragments:
        warnings.append("BRICS did not identify decomposable fragments.")

    return {
        "success": True,
        "version": "2.0",
        "source": "rdkit_native",
        "input_smiles": input_smiles,
        "canonical_smiles": canonical_smiles,
        "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight": round(float(Descriptors.ExactMolWt(mol)), 4),
        "murcko_scaffold_smiles": scaffold_smiles,
        "murcko_scaffold_molblock": scaffold_molblock,
        "generic_scaffold_smiles": generic_scaffold_smiles,
        "brics_fragments": fragments[:80],
        "fragment_count": len(fragments),
        "fragments_truncated": len(fragments) > 80,
        "warnings": warnings,
    }


def fragment_molecule(smiles: Any) -> Tuple[Dict[str, Any], int]:
    """Return a Flask-ready `(payload, status_code)` tuple."""
    try:
        return build_fragmentation_payload(smiles), 200
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except Exception as exc:
        return {"error": str(exc)}, 500
