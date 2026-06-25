"""RDKit-native 3D conformer generation for the v2 chemistry surface."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors


MAX_ATOMS_FOR_INTERACTIVE_3D = 180
DEFAULT_CONFORMERS = 8
MAX_CONFORMERS = 30


def _parse_conformer_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = DEFAULT_CONFORMERS
    return max(1, min(MAX_CONFORMERS, count))


def _build_warnings(mol: Chem.Mol, smiles: str) -> list[str]:
    warnings: list[str] = []
    if "." in smiles:
        warnings.append(
            "Input contains disconnected fragments; RDKit embedded fragments separately."
        )

    if any(atom.HasProp("_ChiralityPossible") for atom in mol.GetAtoms()):
        unassigned = Chem.FindMolChiralCenters(
            mol, includeUnassigned=True, useLegacyImplementation=False
        )
        if any(center[1] == "?" for center in unassigned):
            warnings.append(
                "One or more stereocenters are unspecified; generated 3D geometry is one plausible conformer."
            )

    metal_atomic_numbers = {
        3,
        4,
        11,
        12,
        13,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        37,
        38,
        39,
        40,
        41,
        42,
        44,
        45,
        46,
        47,
        48,
        49,
        50,
        55,
        56,
        57,
        72,
        73,
        74,
        75,
        76,
        77,
        78,
        79,
        80,
        81,
        82,
        83,
    }
    if any(atom.GetAtomicNum() in metal_atomic_numbers for atom in mol.GetAtoms()):
        warnings.append(
            "The molecule contains metal or metalloid atoms; force-field geometry may be approximate."
        )

    if rdMolDescriptors.CalcNumRotatableBonds(mol) > 12:
        warnings.append(
            "Flexible molecule detected; a single conformer may not represent the full conformational ensemble."
        )

    if rdMolDescriptors.CalcNumAtomStereoCenters(mol) > 0:
        warnings.append("3D conformer is computationally generated, not an experimental crystal structure.")

    return warnings


def _embed_conformers(mol: Chem.Mol, count: int) -> list[int]:
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    params.pruneRmsThresh = 0.35
    params.enforceChirality = True
    params.useSmallRingTorsions = True
    params.useMacrocycleTorsions = True
    params.numThreads = 0

    conf_ids = list(AllChem.EmbedMultipleConfs(mol, numConfs=count, params=params))
    if conf_ids:
        return [int(conf_id) for conf_id in conf_ids]

    fallback_status = AllChem.EmbedMolecule(mol, randomSeed=42, useRandomCoords=True)
    if fallback_status < 0:
        return []
    return [int(mol.GetConformer().GetId())]


def _optimize_and_rank(mol: Chem.Mol, conf_ids: list[int], max_iterations: int) -> tuple[str, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []

    if AllChem.MMFFHasAllMoleculeParams(mol):
        properties = AllChem.MMFFGetMoleculeProperties(mol, mmffVariant="MMFF94s")
        for conf_id in conf_ids:
            force_field = AllChem.MMFFGetMoleculeForceField(
                mol, properties, confId=conf_id
            )
            status = int(force_field.Minimize(maxIts=max_iterations))
            rows.append(
                {
                    "id": conf_id,
                    "energy": round(float(force_field.CalcEnergy()), 6),
                    "optimization_status": status,
                }
            )
        return "MMFF94s", rows

    if AllChem.UFFHasAllMoleculeParams(mol):
        for conf_id in conf_ids:
            force_field = AllChem.UFFGetMoleculeForceField(mol, confId=conf_id)
            status = int(force_field.Minimize(maxIts=max_iterations))
            rows.append(
                {
                    "id": conf_id,
                    "energy": round(float(force_field.CalcEnergy()), 6),
                    "optimization_status": status,
                }
            )
        return "UFF", rows

    for conf_id in conf_ids:
        rows.append(
            {
                "id": conf_id,
                "energy": None,
                "optimization_status": None,
            }
        )
    return "none", rows


def build_rdkit_conformer_payload(
    smiles: Any,
    num_conformers: Any = DEFAULT_CONFORMERS,
    max_iterations: Any = 300,
) -> Dict[str, Any]:
    """Build a 3D conformer payload suitable for browser molecular viewers."""
    normalized_smiles = str(smiles or "").strip()
    if not normalized_smiles:
        raise ValueError("SMILES string is required")

    mol = Chem.MolFromSmiles(normalized_smiles)
    if mol is None:
        raise ValueError("Invalid SMILES string")

    atom_count = int(mol.GetNumAtoms())
    if atom_count < 2:
        raise ValueError("3D conformer generation requires at least two atoms")
    if atom_count > MAX_ATOMS_FOR_INTERACTIVE_3D:
        raise ValueError(
            f"Interactive 3D generation is limited to {MAX_ATOMS_FOR_INTERACTIVE_3D} heavy atoms"
        )

    try:
        iteration_count = int(max_iterations)
    except (TypeError, ValueError):
        iteration_count = 300
    iteration_count = max(50, min(1000, iteration_count))

    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    warnings = _build_warnings(mol, normalized_smiles)
    mol_3d = Chem.AddHs(mol)
    conformer_count = _parse_conformer_count(num_conformers)

    conf_ids = _embed_conformers(mol_3d, conformer_count)
    if not conf_ids:
        raise ValueError("RDKit failed to generate a 3D conformer for this molecule")

    force_field_name, conformer_rows = _optimize_and_rank(
        mol_3d, conf_ids, iteration_count
    )
    if force_field_name == "none":
        warnings.append(
            "No supported RDKit force-field parameters were available; geometry was embedded but not optimized."
        )

    best = min(
        conformer_rows,
        key=lambda row: float("inf") if row["energy"] is None else float(row["energy"]),
    )
    best_conf_id = int(best["id"])

    return {
        "success": True,
        "version": "2.0",
        "source": "rdkit_native",
        "viewer": "3dmol",
        "input_smiles": normalized_smiles,
        "canonical_smiles": canonical_smiles,
        "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight": round(float(Descriptors.ExactMolWt(mol)), 4),
        "heavy_atom_count": atom_count,
        "atom_count_with_hydrogens": int(mol_3d.GetNumAtoms()),
        "bond_count": int(mol.GetNumBonds()),
        "conformer_count": len(conformer_rows),
        "best_conformer_id": best_conf_id,
        "energy": best["energy"],
        "force_field": force_field_name,
        "optimization_status": best["optimization_status"],
        "molblock": Chem.MolToMolBlock(mol_3d, confId=best_conf_id),
        "pdb_block": Chem.MolToPDBBlock(mol_3d, confId=best_conf_id),
        "conformers": conformer_rows,
        "warnings": warnings,
    }


def generate_conformer(
    smiles: Any,
    num_conformers: Any = DEFAULT_CONFORMERS,
    max_iterations: Any = 300,
) -> Tuple[Dict[str, Any], int]:
    """Return a Flask-ready `(payload, status_code)` tuple."""
    try:
        return (
            build_rdkit_conformer_payload(
                smiles=smiles,
                num_conformers=num_conformers,
                max_iterations=max_iterations,
            ),
            200,
        )
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except Exception as exc:
        return {"error": str(exc)}, 500
