"""Curated high-confidence molecule aliases for deterministic resolution.

This table is intentionally small. It covers common compounds that users often
name in Chinese or English, and it is used before LLM or external lookups.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class KnownMolecule:
    canonical_name: str
    canonical_smiles: str
    aliases: tuple[str, ...]


_KNOWN_MOLECULES: tuple[KnownMolecule, ...] = (
    KnownMolecule(
        canonical_name="aspirin",
        canonical_smiles="CC(=O)Oc1ccccc1C(=O)O",
        aliases=("aspirin", "acetylsalicylic acid", "阿司匹林", "乙酰水杨酸"),
    ),
    KnownMolecule(
        canonical_name="acetaminophen",
        canonical_smiles="CC(=O)Nc1ccc(O)cc1",
        aliases=("acetaminophen", "paracetamol", "对乙酰氨基酚", "扑热息痛"),
    ),
    KnownMolecule(
        canonical_name="ethanol",
        canonical_smiles="CCO",
        aliases=("ethanol", "ethyl alcohol", "乙醇", "酒精"),
    ),
    KnownMolecule(
        canonical_name="benzene",
        canonical_smiles="c1ccccc1",
        aliases=("benzene", "苯"),
    ),
    KnownMolecule(
        canonical_name="toluene",
        canonical_smiles="Cc1ccccc1",
        aliases=("toluene", "methylbenzene", "甲苯"),
    ),
    KnownMolecule(
        canonical_name="benzoic acid",
        canonical_smiles="O=C(O)c1ccccc1",
        aliases=("benzoic acid", "benzenecarboxylic acid", "苯甲酸"),
    ),
    KnownMolecule(
        canonical_name="acetic acid",
        canonical_smiles="CC(=O)O",
        aliases=("acetic acid", "ethanoic acid", "乙酸", "醋酸"),
    ),
    KnownMolecule(
        canonical_name="water",
        canonical_smiles="O",
        aliases=("water", "oxidane", "水"),
    ),
    KnownMolecule(
        canonical_name="carbon dioxide",
        canonical_smiles="O=C=O",
        aliases=("carbon dioxide", "二氧化碳"),
    ),
    KnownMolecule(
        canonical_name="salicylic acid",
        canonical_smiles="O=C(O)c1ccccc1O",
        aliases=("salicylic acid", "水杨酸"),
    ),
    KnownMolecule(
        canonical_name="acetic anhydride",
        canonical_smiles="CC(=O)OC(C)=O",
        aliases=("acetic anhydride", "乙酸酐", "醋酸酐"),
    ),
    KnownMolecule(
        canonical_name="molecular oxygen",
        canonical_smiles="O=O",
        aliases=("molecular oxygen", "dioxygen", "oxygen", "oxygen gas", "氧气", "分子氧"),
    ),
    KnownMolecule(
        canonical_name="molecular hydrogen",
        canonical_smiles="[H][H]",
        aliases=("molecular hydrogen", "hydrogen gas", "hydrogen", "氢气", "分子氢"),
    ),
    KnownMolecule(
        canonical_name="molecular nitrogen",
        canonical_smiles="N#N",
        aliases=("molecular nitrogen", "dinitrogen", "nitrogen gas", "nitrogen", "氮气", "分子氮"),
    ),
    KnownMolecule(
        canonical_name="molecular fluorine",
        canonical_smiles="FF",
        aliases=("molecular fluorine", "fluorine gas", "fluorine", "氟气", "分子氟"),
    ),
    KnownMolecule(
        canonical_name="molecular chlorine",
        canonical_smiles="ClCl",
        aliases=("molecular chlorine", "chlorine gas", "chlorine", "氯气", "分子氯"),
    ),
    KnownMolecule(
        canonical_name="molecular bromine",
        canonical_smiles="BrBr",
        aliases=("molecular bromine", "bromine", "bromine liquid", "溴", "溴单质", "分子溴"),
    ),
    KnownMolecule(
        canonical_name="molecular iodine",
        canonical_smiles="II",
        aliases=("molecular iodine", "iodine", "iodine solid", "碘", "碘单质", "分子碘"),
    ),
)


def _normalize_alias(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[\s_\-:：,，.;；()（）\[\]【】]+", "", text)


_EXACT_ALIASES: dict[str, KnownMolecule] = {
    _normalize_alias(alias): molecule
    for molecule in _KNOWN_MOLECULES
    for alias in molecule.aliases
}


def resolve_known_molecule(value: Any) -> KnownMolecule | None:
    """Resolve an exact high-confidence alias."""
    return _EXACT_ALIASES.get(_normalize_alias(value))


def extract_known_molecule(value: Any) -> KnownMolecule | None:
    """Return a known molecule mentioned inside a larger user request.

    If multiple known aliases are present, return None so the caller does not
    silently choose one molecule from a comparative or multi-part request.
    """
    normalized = _normalize_alias(value)
    if not normalized:
        return None
    matches: list[KnownMolecule] = []
    matched_aliases: list[str] = []
    for alias, molecule in sorted(_EXACT_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if any(alias != matched_alias and alias in matched_alias for matched_alias in matched_aliases):
            continue
        if alias and alias in normalized and molecule not in matches:
            matches.append(molecule)
            matched_aliases.append(alias)
    return matches[0] if len(matches) == 1 else None


def extract_known_molecules(value: Any) -> tuple[KnownMolecule, ...]:
    """Return all distinct known molecules mentioned inside a larger request."""
    normalized = _normalize_alias(value)
    if not normalized:
        return ()
    matches: list[KnownMolecule] = []
    matched_aliases: list[str] = []
    for alias, molecule in sorted(_EXACT_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if any(alias != matched_alias and alias in matched_alias for matched_alias in matched_aliases):
            continue
        if alias and alias in normalized and molecule not in matches:
            matches.append(molecule)
            matched_aliases.append(alias)
    return tuple(matches)


__all__ = [
    "KnownMolecule",
    "extract_known_molecule",
    "extract_known_molecules",
    "resolve_known_molecule",
]
