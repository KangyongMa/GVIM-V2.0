"""RDKit-native molecular descriptor service used by v2 chemistry routes."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors


ALLOWED_ANALYSIS_TYPES = {
    "rdkit_descriptors",
}


def _normalize_analysis_type(value: Any) -> str:
    normalized = str(value or "rdkit_descriptors").strip().lower()
    if normalized not in ALLOWED_ANALYSIS_TYPES:
        return "rdkit_descriptors"
    return normalized


def build_rdkit_descriptor_payload(
    smiles: Any,
    analysis_type: Any = "rdkit_descriptors",
) -> Dict[str, Any]:
    """Build the canonical RDKit descriptor payload."""
    normalized_smiles = str(smiles or "").strip()
    if not normalized_smiles:
        raise ValueError("SMILES string is required")

    mol = Chem.MolFromSmiles(normalized_smiles)
    if mol is None:
        raise ValueError("Invalid SMILES string")

    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    normalized_analysis_type = _normalize_analysis_type(analysis_type)

    descriptors_payload = {
        "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight": round(float(Descriptors.ExactMolWt(mol)), 4),
        "average_molecular_weight": round(float(Descriptors.MolWt(mol)), 4),
        "logp": round(float(Descriptors.MolLogP(mol)), 4),
        "tpsa": round(float(Descriptors.TPSA(mol)), 4),
        "hba": int(rdMolDescriptors.CalcNumHBA(mol)),
        "hbd": int(rdMolDescriptors.CalcNumHBD(mol)),
        "rotatable_bonds": int(rdMolDescriptors.CalcNumRotatableBonds(mol)),
        "num_rings": int(rdMolDescriptors.CalcNumRings(mol)),
        "num_aromatic_rings": int(rdMolDescriptors.CalcNumAromaticRings(mol)),
        "heavy_atom_count": int(mol.GetNumHeavyAtoms()),
        "formal_charge": int(sum(atom.GetFormalCharge() for atom in mol.GetAtoms())),
        "fraction_csp3": round(float(rdMolDescriptors.CalcFractionCSP3(mol)), 6),
    }

    return {
        "success": True,
        "version": "3.0",
        "analysis_type": normalized_analysis_type,
        "source": "rdkit_native_descriptors",
        "smiles": normalized_smiles,
        "canonical_smiles": canonical_smiles,
        "descriptors": descriptors_payload,
        "data_quality": {
            "computed_from": "smiles",
            "engine": "rdkit",
            "external_database_lookup": False,
            "experimental": False,
        },
    }


def describe_molecule(
    smiles: Any,
    analysis_type: Any = "rdkit_descriptors",
) -> Tuple[Dict[str, Any], int]:
    """Return a Flask-ready `(payload, status_code)` tuple."""
    try:
        return build_rdkit_descriptor_payload(smiles, analysis_type), 200
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except Exception as exc:
        return {"error": str(exc)}, 500
