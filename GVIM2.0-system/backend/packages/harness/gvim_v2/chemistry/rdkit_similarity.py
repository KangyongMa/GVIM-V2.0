"""RDKit Morgan fingerprint similarity for the v2 chemistry surface."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import Descriptors, rdFingerprintGenerator, rdMolDescriptors


RDLogger.DisableLog("rdApp.error")

MAX_MOLECULES = 8


def _parse_positive_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _molecule_summary(index: int, smiles: str, mol: Chem.Mol) -> dict[str, Any]:
    return {
        "index": index,
        "input_smiles": smiles,
        "canonical_smiles": Chem.MolToSmiles(mol, canonical=True),
        "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight": round(float(Descriptors.ExactMolWt(mol)), 4),
        "heavy_atom_count": int(mol.GetNumAtoms()),
    }


def build_similarity_payload(
    smiles_list: Any,
    radius: Any = 2,
    n_bits: Any = 2048,
) -> Dict[str, Any]:
    """Build pairwise Morgan fingerprint similarity for 2-8 SMILES strings."""
    if not isinstance(smiles_list, list):
        raise ValueError("smiles_list must be a list")

    cleaned_smiles = [str(item or "").strip() for item in smiles_list]
    cleaned_smiles = [item for item in cleaned_smiles if item]
    if len(cleaned_smiles) < 2:
        raise ValueError("At least two SMILES strings are required")
    if len(cleaned_smiles) > MAX_MOLECULES:
        raise ValueError(f"Similarity comparison is limited to {MAX_MOLECULES} molecules")

    parsed: list[tuple[str, Chem.Mol]] = []
    for smiles in cleaned_smiles:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"Invalid SMILES string: {smiles}")
        parsed.append((smiles, mol))

    fingerprint_radius = _parse_positive_int(radius, default=2, minimum=1, maximum=4)
    fingerprint_bits = _parse_positive_int(n_bits, default=2048, minimum=512, maximum=4096)
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=fingerprint_radius,
        fpSize=fingerprint_bits,
    )
    fingerprints = [generator.GetFingerprint(mol) for _, mol in parsed]
    molecules = [
        _molecule_summary(index, smiles, mol)
        for index, (smiles, mol) in enumerate(parsed)
    ]

    pairwise: list[dict[str, Any]] = []
    for left_index in range(len(fingerprints)):
        for right_index in range(left_index + 1, len(fingerprints)):
            pairwise.append(
                {
                    "left_index": left_index,
                    "right_index": right_index,
                    "left_smiles": molecules[left_index]["canonical_smiles"],
                    "right_smiles": molecules[right_index]["canonical_smiles"],
                    "tanimoto": round(
                        float(
                            DataStructs.TanimotoSimilarity(
                                fingerprints[left_index],
                                fingerprints[right_index],
                            )
                        ),
                        6,
                    ),
                }
            )

    pairwise.sort(key=lambda item: item["tanimoto"], reverse=True)
    similarity_matrix = [[1.0 for _ in fingerprints] for _ in fingerprints]
    for item in pairwise:
        left = int(item["left_index"])
        right = int(item["right_index"])
        score = float(item["tanimoto"])
        similarity_matrix[left][right] = score
        similarity_matrix[right][left] = score

    return {
        "success": True,
        "version": "2.0",
        "source": "rdkit_native",
        "fingerprint": {
            "type": "morgan",
            "radius": fingerprint_radius,
            "n_bits": fingerprint_bits,
        },
        "count": len(molecules),
        "molecule_count": len(molecules),
        "molecules": molecules,
        "similarity_matrix": similarity_matrix,
        "pairwise": pairwise,
        "most_similar_pair": pairwise[0] if pairwise else None,
    }


def compare_similarity(
    smiles_list: Any,
    radius: Any = 2,
    n_bits: Any = 2048,
) -> Tuple[Dict[str, Any], int]:
    """Return a Flask-ready `(payload, status_code)` tuple."""
    try:
        return build_similarity_payload(smiles_list, radius=radius, n_bits=n_bits), 200
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except Exception as exc:
        return {"error": str(exc)}, 500
