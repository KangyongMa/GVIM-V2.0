"""LLM-driven Ketcher canvas preparation for natural-language chemistry requests."""

from __future__ import annotations

import json
import re
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors, rdChemReactions, rdDepictor, rdMolDescriptors

from gvim_v2.chemistry.ketcher_commands import (
    KETCHER_STRUCTURE_COMMAND_TYPES,
    ketcher_commands_from_payload,
    with_ketcher_commands,
)
from gvim_v2.chemistry.known_molecules import (
    extract_known_molecule,
    extract_known_molecules,
    resolve_known_molecule,
)
from gvim_v2.chemistry.llm_json import post_chemistry_llm_json
from gvim_v2.chemistry.structure_resolution import (
    _canonicalize_smiles,
    _resolve_with_opsin,
    _resolve_with_pubchem,
    build_structure_resolution_payload,
)


def _molblock_from_smiles(smiles: str) -> str:
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return ""
        rdDepictor.Compute2DCoords(mol)
        return Chem.MolToMolBlock(mol)
    except Exception:
        return ""


def _rxnblock_from_reaction_smiles(reaction: str) -> str:
    try:
        rxn = rdChemReactions.ReactionFromSmarts(reaction, useSmiles=True)
        if rxn is None:
            return ""
        return rdChemReactions.ReactionToRxnBlock(rxn)
    except Exception:
        return ""


def _structure_summary_from_smiles(smiles: str) -> dict[str, Any] | None:
    canonical = _canonicalize_smiles(smiles)
    if not canonical:
        return None

    mol = Chem.MolFromSmiles(canonical)
    if mol is None:
        return None

    molblock = _molblock_from_smiles(canonical)
    return {
        "smiles": canonical,
        "canonical_smiles": canonical,
        "molfile": molblock,
        "molblock": molblock,
        "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight": round(float(Descriptors.ExactMolWt(mol)), 4),
        "num_atoms": int(mol.GetNumAtoms()),
        "num_bonds": int(mol.GetNumBonds()),
        "logP": round(float(Descriptors.MolLogP(mol)), 4),
        "tpsa": round(float(Descriptors.TPSA(mol)), 4),
    }


def _structure_summary_from_resolution(resolution: dict[str, Any]) -> dict[str, Any]:
    smiles = str(resolution.get("canonical_smiles") or "").strip()
    summary = _structure_summary_from_smiles(smiles)
    if summary:
        return summary
    return {
        "smiles": smiles,
        "canonical_smiles": smiles,
        "molecular_formula": resolution.get("molecular_formula") or "",
        "molecular_weight": resolution.get("molecular_weight"),
        "num_atoms": resolution.get("heavy_atom_count"),
        "num_bonds": None,
    }


def _canonicalize_reaction_smiles(reaction: str) -> str:
    normalized = str(reaction or "").replace("->", ">>").replace("=>", ">>").replace("\u2192", ">>")
    if ">>" not in normalized:
        return ""

    left, right = normalized.split(">>", 1)
    reactants = [item.strip() for item in left.split(".") if item.strip()]
    products = [item.strip() for item in right.split(".") if item.strip()]
    if not reactants or not products:
        return ""

    canonical_reactants = [_canonicalize_smiles(item) for item in reactants]
    canonical_products = [_canonicalize_smiles(item) for item in products]
    if not all(canonical_reactants) or not all(canonical_products):
        return ""
    return f"{'.'.join(canonical_reactants)}>>{'.'.join(canonical_products)}"


def _split_canonical_reaction_smiles(reaction: str) -> tuple[list[str], list[str]]:
    canonical = _canonicalize_reaction_smiles(reaction)
    if not canonical:
        return [], []
    left, right = canonical.split(">>", 1)
    return (
        [item.strip() for item in left.split(".") if item.strip()],
        [item.strip() for item in right.split(".") if item.strip()],
    )


def _user_request_text(raw_query: str) -> str:
    text = str(raw_query or "")
    markers = (
        "ATTACHED CONTEXT",
        "Attached context",
        "ACTIVE CONTEXT",
        "Active context",
        "CURRENT CONTEXT",
        "Current context",
        "附加上下文",
        "当前上下文",
    )
    indexes = [text.find(marker) for marker in markers if text.find(marker) >= 0]
    if indexes:
        text = text[: min(indexes)]
    return text.strip()


def _evidence_text(value: Any) -> str:
    text = str(value or "").strip().casefold()
    return re.sub(r"[\s_\-:;,.(){}\[\]<>/\\|\"'`~!@#$%^&*+=?]+", "", text)


def _query_has_reaction_arrow(raw_query: str) -> bool:
    return bool(re.search(r"(>>|->|=>|\u2192)", str(raw_query or "")))


def _query_has_product_language(raw_query: str) -> bool:
    text = str(raw_query or "")
    compact = _evidence_text(text)
    chinese_markers = (
        "\u751f\u6210",
        "\u5f97\u5230",
        "\u4ea7\u7269",
        "\u8f6c\u5316\u4e3a",
        "\u53d8\u6210",
        "\u5f62\u6210",
    )
    if any(marker in compact for marker in chinese_markers):
        return True
    return bool(
        re.search(
            r"\b(to|into|yield|yields|give|gives|form|forms|produce|produces|product)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _query_mentions_name_or_alias(name: str, raw_query: str) -> bool:
    name_key = _evidence_text(name)
    query_key = _evidence_text(raw_query)
    if name_key and name_key in query_key:
        return True

    known = resolve_known_molecule(name)
    if known is None:
        return False
    return any(
        alias_key and alias_key in query_key
        for alias_key in (_evidence_text(alias) for alias in known.aliases)
    )


def _planned_product_entries(plan: dict[str, Any]) -> list[dict[str, str]]:
    return _planned_participant_entries(plan, "products")


def _planned_participant_entries(
    plan: dict[str, Any],
    side_key: str,
) -> list[dict[str, str]]:
    entries = _participant_entries(plan.get(side_key))
    raw_steps = plan.get("steps")
    if isinstance(raw_steps, list):
        for step in raw_steps[:4]:
            if isinstance(step, dict):
                entries.extend(_participant_entries(step.get(side_key)))
    return entries


def _entry_candidate_smiles(entry: dict[str, str]) -> list[str]:
    candidates: list[str] = []
    provided = _canonicalize_smiles(str(entry.get("smiles") or "").strip())
    if provided:
        candidates.append(provided)

    known = resolve_known_molecule(entry.get("name") or "")
    if known is not None:
        known_smiles = _canonicalize_smiles(known.canonical_smiles)
        if known_smiles and known_smiles not in candidates:
            candidates.append(known_smiles)
    return candidates


def _component_supported_by_planned_entry(
    component: str,
    entries: list[dict[str, str]],
    raw_query: str,
) -> bool:
    for entry in entries:
        name = str(entry.get("name") or "").strip()
        if not name or not _query_mentions_name_or_alias(name, raw_query):
            continue
        if any(
            _same_molecule_connectivity(component, candidate)
            for candidate in _entry_candidate_smiles(entry)
        ):
            return True
    return False


def _reaction_component_evidence_report(
    *,
    reaction: str,
    plan: dict[str, Any],
    raw_query: str,
) -> dict[str, Any]:
    reactants, products = _split_canonical_reaction_smiles(reaction)
    if not reactants or not products:
        return {
            "supported": False,
            "unsupported_components": [{"side": "reaction", "smiles": reaction}],
        }

    entries_by_side = {
        "reactant": _planned_participant_entries(plan, "reactants"),
        "product": _planned_participant_entries(plan, "products"),
    }
    unsupported: list[dict[str, str]] = []
    for side, components in (("reactant", reactants), ("product", products)):
        entries = entries_by_side[side]
        if not entries:
            unsupported.extend({"side": side, "smiles": component} for component in components)
            continue
        for component in components:
            if not _component_supported_by_planned_entry(component, entries, raw_query):
                unsupported.append({"side": side, "smiles": component})

    return {
        "supported": not unsupported,
        "unsupported_components": unsupported,
        "reactant_evidence_count": len(entries_by_side["reactant"]),
        "product_evidence_count": len(entries_by_side["product"]),
    }


def _query_mentions_reaction_product(
    *,
    reaction: str,
    plan: dict[str, Any],
    raw_query: str,
    require_product_language: bool = True,
) -> bool:
    if require_product_language and not _query_has_product_language(raw_query):
        return False

    for entry in _planned_product_entries(plan):
        if _query_mentions_name_or_alias(entry.get("name") or "", raw_query):
            return True

    _reactants, products = _split_canonical_reaction_smiles(reaction)
    for known in extract_known_molecules(raw_query):
        known_smiles = _canonicalize_smiles(known.canonical_smiles)
        if known_smiles and any(_same_molecule_connectivity(product, known_smiles) for product in products):
            return True
    return False


def _reaction_guardrail_payload(
    *,
    raw_query: str,
    reply: str = "",
    confidence: float | None = None,
    guardrail: str = "missing_user_supported_reaction_product",
    warning: str = "Reaction drawing is blocked until the product identity is user-supported.",
) -> dict[str, Any]:
    default_reply = (
        "This reaction request only provides reactants or an underspecified reaction. "
        "Please specify the product, reaction type, or a complete reaction SMILES before drawing."
    )
    if guardrail == "invalid_generated_elemental_species":
        default_reply = (
            "The planner produced a single-atom elemental species for a generated "
            "reaction drawing. Elemental gases or halogens must be represented by "
            "their resolved molecular structures, and generated single atoms will "
            "not be loaded into Ketcher. Please provide a complete reaction SMILES "
            "or explicitly name every reactant and product."
        )
    elif guardrail == "unsupported_reaction_components":
        default_reply = (
            "The planner added reaction components that were not supported by the user's request. "
            "Please provide the complete reaction SMILES or explicitly name every reactant and product to draw."
        )
    return {
        "success": False,
        "version": "2.0",
        "intent": "draw_reaction",
        "mode": "studio_prepare",
        "requires_input": True,
        "reply": reply or default_reply,
        "ketcher_commands": [],
        "current_structure": None,
        "analysis": {
            "primary_tool": "chemistry_prepare_studio",
            "kind": "reaction",
            "source": "agent_evidence_gate",
            "guardrail": guardrail,
            "planner_confidence": confidence,
            "raw_query": raw_query,
        },
        "warnings": [warning],
    }


def _is_evidence_gate_payload(payload: dict[str, Any]) -> bool:
    analysis = payload.get("analysis")
    return (
        isinstance(analysis, dict)
        and analysis.get("guardrail")
        in {
            "missing_user_supported_reaction_product",
            "invalid_generated_elemental_species",
            "unsupported_reaction_components",
        }
    )


_GENERATED_SINGLE_ATOM_ELEMENT_RE = re.compile(
    r"^\[(?:H|N|O|F|Cl|Br|I)(?::\d+)?\]$"
)


def _is_generated_single_atom_element_component(component: str) -> bool:
    """Return true for generated single-atom elemental components.

    This guard is intentionally limited to generated reactions. Explicit
    user-supplied reaction SMILES are preserved before the planner path, because
    the user may intentionally request an atom/radical.
    """
    return bool(_GENERATED_SINGLE_ATOM_ELEMENT_RE.fullmatch(str(component or "").strip()))


def _reaction_has_generated_single_atom_element(reaction: str) -> bool:
    reactants, products = _split_canonical_reaction_smiles(reaction)
    return any(
        _is_generated_single_atom_element_component(component)
        for component in [*reactants, *products]
    )


def _context_window_has_reaction_draft_marker(query: str, start: int) -> bool:
    prefix = str(query or "")[max(0, start - 180):start].casefold()
    compact = _evidence_text(prefix)
    context_markers = (
        "attachedcontext",
        "activecontext",
        "reactiondraftfromstudio",
        "reactiondraftfromstudiorequest",
        "fromthechemistrystudio",
        "activereactioncontext",
        "currentreactioncontext",
        "previousreaction",
        "\u4e0a\u4e0b\u6587",
        "\u9644\u52a0\u4e0a\u4e0b\u6587",
        "\u5f53\u524d\u53cd\u5e94",
        "\u4e0a\u4e00\u6b65\u53cd\u5e94",
    )
    return any(marker in compact for marker in context_markers)


def _looks_like_direct_user_reaction_smiles(query: str, match: re.Match[str]) -> bool:
    candidate = match.group(1).strip()
    text = str(query or "").strip()
    if _evidence_text(text) == _evidence_text(candidate):
        return True
    if match.start() == 0 and candidate:
        return True
    if _context_window_has_reaction_draft_marker(text, match.start()):
        return False
    prefix = text[max(0, match.start() - 80):match.start()].casefold()
    return bool(
        re.search(
            r"(draw|sketch|load|open|reaction|rxn|smiles|绘制|画|加载|反应式|反应\s*)\s*[:：]?\s*$",
            prefix,
            flags=re.IGNORECASE,
        )
    )


_REACTION_SMILES_RE = re.compile(
    r"([A-Za-z0-9@+\-\[\]\(\)=#$\\/%.:]+(?:\.[A-Za-z0-9@+\-\[\]\(\)=#$\\/%.:]+)*"
    r"(?:>>|->|=>|\u2192)"
    r"[A-Za-z0-9@+\-\[\]\(\)=#$\\/%.:]+(?:\.[A-Za-z0-9@+\-\[\]\(\)=#$\\/%.:]+)*)"
)


def _extract_user_reaction_smiles(query: str) -> str:
    """Extract a user-supplied reaction SMILES without invoking the planner."""
    raw_query = str(query or "")
    for match in _REACTION_SMILES_RE.finditer(raw_query):
        if not _looks_like_direct_user_reaction_smiles(raw_query, match):
            continue
        reaction = _canonicalize_reaction_smiles(match.group(1))
        if reaction:
            return reaction
    return ""


def _is_direct_molecule_canvas_request(query: str) -> bool:
    text = str(query or "").strip().lower()
    if any(
        token in text
        for token in (
            "reaction",
            "synthesis",
            "route",
            "compare",
            "比较",
            "对比",
            "反应",
            "合成",
            "路线",
        )
    ):
        return False
    return any(
        token in text
        for token in (
            "draw",
            "sketch",
            "open",
            "load",
            "ketcher",
            "绘制",
            "画出",
            "打开",
            "载入",
        )
    )


def _inchi_connectivity_key(smiles: str) -> str:
    mol = Chem.MolFromSmiles(str(smiles or "").strip())
    if mol is None:
        return ""
    try:
        return str(Chem.MolToInchiKey(mol) or "").split("-", 1)[0]
    except Exception:
        return ""


def _same_molecule_connectivity(left_smiles: str, right_smiles: str) -> bool:
    left_key = _inchi_connectivity_key(left_smiles)
    right_key = _inchi_connectivity_key(right_smiles)
    if left_key and right_key:
        return left_key == right_key
    return _canonicalize_smiles(left_smiles) == _canonicalize_smiles(right_smiles)


def _planned_target_lookup(plan: dict[str, Any]) -> str:
    return str(
        plan.get("pubchem_lookup")
        or plan.get("target_name")
        or plan.get("resolved_name")
        or ""
    ).strip()


def _resolve_target_with_external_name_services(
    target: str,
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    lookup = str(target or "").strip()
    if not lookup:
        return {"success": False}

    known_molecule = resolve_known_molecule(lookup)
    if known_molecule is not None:
        canonical = _canonicalize_smiles(known_molecule.canonical_smiles)
        if canonical:
            return {
                "success": True,
                "source": "local_curated_alias",
                "resolved_name": known_molecule.canonical_name,
                "canonical_smiles": canonical,
                "confidence": 1.0,
            }

    for source, resolver, confidence in (
        ("llm_guided_pubchem", _resolve_with_pubchem, 0.9),
        ("llm_guided_opsin", _resolve_with_opsin, 0.88),
    ):
        hit = resolver(lookup, timeout)
        if not hit:
            continue
        smiles, resolved_name = hit
        canonical = _canonicalize_smiles(smiles)
        if canonical:
            return {
                "success": True,
                "source": source,
                "resolved_name": resolved_name or lookup,
                "canonical_smiles": canonical,
                "confidence": confidence,
            }
    return {"success": False}


def _participant_entries(raw_entries: Any) -> list[dict[str, str]]:
    if not isinstance(raw_entries, list):
        return []

    entries: list[dict[str, str]] = []
    for raw_entry in raw_entries[:8]:
        if isinstance(raw_entry, str):
            name = raw_entry.strip()
            smiles = ""
        elif isinstance(raw_entry, dict):
            name = str(
                raw_entry.get("name")
                or raw_entry.get("label")
                or raw_entry.get("compound")
                or ""
            ).strip()
            smiles = str(
                raw_entry.get("smiles")
                or raw_entry.get("canonical_smiles")
                or ""
            ).strip()
        else:
            continue
        if name or smiles:
            entries.append({"name": name, "smiles": smiles})
    return entries


def _resolve_planned_participant(
    entry: dict[str, str],
    *,
    allow_pubchem: bool,
    lookup_timeout: float = 10.0,
) -> tuple[str, dict[str, Any]]:
    name = str(entry.get("name") or "").strip()
    provided_smiles = _canonicalize_smiles(str(entry.get("smiles") or "").strip())

    if name:
        resolution = build_structure_resolution_payload(
            name,
            allow_pubchem=allow_pubchem,
            timeout=lookup_timeout,
        )
        resolved_smiles = str(resolution.get("canonical_smiles") or "").strip()
        if resolution.get("success") and resolved_smiles:
            return resolved_smiles, {
                "name": name,
                "source": resolution.get("source") or "llm_structure_resolution",
                "resolved_name": resolution.get("resolved_name") or name,
                "smiles": resolved_smiles,
                "provided_smiles": provided_smiles or None,
                "used": "resolved_name",
            }

    if provided_smiles:
        return provided_smiles, {
            "name": name or None,
            "source": "llm_participant_smiles",
            "smiles": provided_smiles,
            "used": "provided_smiles",
        }

    return "", {
        "name": name or None,
        "source": "unresolved_participant",
        "used": "none",
    }


def _reaction_from_planned_participants(
    item: dict[str, Any],
    *,
    allow_pubchem: bool,
    lookup_timeout: float = 10.0,
) -> tuple[str, list[dict[str, Any]]]:
    reactant_entries = _participant_entries(item.get("reactants"))
    product_entries = _participant_entries(item.get("products"))
    if not reactant_entries or not product_entries:
        return "", []

    participant_resolution: list[dict[str, Any]] = []
    reactants: list[str] = []
    products: list[str] = []

    for entry in reactant_entries:
        smiles, metadata = _resolve_planned_participant(
            entry,
            allow_pubchem=allow_pubchem,
            lookup_timeout=lookup_timeout,
        )
        metadata["side"] = "reactant"
        participant_resolution.append(metadata)
        if smiles:
            reactants.append(smiles)

    for entry in product_entries:
        smiles, metadata = _resolve_planned_participant(
            entry,
            allow_pubchem=allow_pubchem,
            lookup_timeout=lookup_timeout,
        )
        metadata["side"] = "product"
        participant_resolution.append(metadata)
        if smiles:
            products.append(smiles)

    if len(reactants) != len(reactant_entries) or len(products) != len(product_entries):
        return "", participant_resolution

    reaction = _canonicalize_reaction_smiles(
        f"{'.'.join(reactants)}>>{'.'.join(products)}"
    )
    return reaction, participant_resolution


def _participant_entries_with_resolution(
    entries: list[dict[str, str]],
    participant_resolution: list[dict[str, Any]],
    side: str,
) -> list[dict[str, str]]:
    side_resolution = [
        item
        for item in participant_resolution
        if str(item.get("side") or "") == side
    ]
    if not side_resolution:
        return entries

    enriched: list[dict[str, str]] = []
    for index, entry in enumerate(entries):
        next_entry = dict(entry)
        resolved_smiles = str(
            side_resolution[index].get("smiles") if index < len(side_resolution) else ""
        ).strip()
        if resolved_smiles and not next_entry.get("smiles"):
            next_entry["smiles"] = resolved_smiles
        enriched.append(next_entry)
    return enriched


def _extract_reaction_participants_with_llm(
    *,
    raw_query: str,
    reaction: str,
    note: str = "",
    llm_timeout: float = 30.0,
) -> dict[str, Any]:
    if not raw_query.strip() or not reaction.strip():
        return {}

    parsed, _settings = post_chemistry_llm_json(
        mode="smart",
        temperature=0.0,
        max_tokens=550,
        timeout=llm_timeout,
        messages=[
            {
                "role": "system",
                "content": (
                    "You validate chemistry canvas reactions. Return strict JSON only with "
                    "schema {\"reactants\":[{\"name\":\"\",\"smiles\":\"\"}],"
                    "\"products\":[{\"name\":\"\",\"smiles\":\"\"}],\"confidence\":0.0}. "
                    "Use the user's request as the source of truth for compound identities. "
                    "If a candidate reaction SMILES conflicts with a named participant, keep "
                    "the participant name and provide the corrected SMILES for that name. "
                    "Do not add lab conditions or operational instructions."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User request: {raw_query}\n"
                    f"Candidate reaction SMILES: {reaction}\n"
                    f"Planner note: {note}"
                ),
            },
        ],
    )
    return parsed if isinstance(parsed, dict) else {}


def _plan_studio_request_with_llm(query: str, *, llm_timeout: float = 30.0) -> dict[str, Any] | None:
    parsed, _settings = post_chemistry_llm_json(
        mode="smart",
        temperature=0.1,
        max_tokens=900,
        timeout=llm_timeout,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the Chemistry Studio canvas planner. Return strict JSON only with "
                    "schema {\"kind\":\"molecule|reaction|synthesis_route|unsupported\","
                    "\"reply\":\"\",\"target_name\":\"\",\"smiles\":\"\",\"reaction\":\"\","
                    "\"reactants\":[{\"name\":\"\",\"smiles\":\"\"}],"
                    "\"products\":[{\"name\":\"\",\"smiles\":\"\"}],"
                    "\"steps\":[{\"reaction\":\"A.B>>C\",\"reactants\":[{\"name\":\"\",\"smiles\":\"\"}],"
                    "\"products\":[{\"name\":\"\",\"smiles\":\"\"}],\"conditions\":\"\",\"note\":\"\"}],"
                    "\"pubchem_lookup\":\"\",\"requires_input\":false,\"confidence\":0.0}. "
                    "Understand user intent from natural-language English or Chinese. "
                    "Requests such as 绘制, 画出, 在Ketcher中绘制, draw, sketch, open, or load "
                    "are canvas drawing requests. Do not mark them unsupported just because "
                    "they are phrased in Chinese or contain UI words. "
                    "For molecule drawing, provide a valid SMILES when highly confident or a "
                    "target_name/pubchem_lookup for resolver lookup. For Chinese compound "
                    "names, provide an English PubChem lookup name when possible. Always include "
                    "the best target_name/pubchem_lookup when you output a SMILES so the service "
                    "can independently verify the identity. "
                    "For complex natural-language structures, explicitly preserve substituent "
                    "positions, stereochemistry, salts/charges, isotopes, tautomer/protonation "
                    "state, and ring/fused-system details. Never simplify a complex request to a "
                    "common parent scaffold. If several regioisomers, stereoisomers, tautomers, "
                    "or salt forms are possible, set requires_input=true and ask a focused "
                    "clarifying question instead of drawing a guess. "
                    "For reaction drawing, provide a full reaction SMILES only when the user "
                    "explicitly supplies a reaction SMILES or clearly states both reactants "
                    "and products. If the user supplies only reactants or a reaction family, "
                    "set requires_input=true and ask for the missing product or reaction type; "
                    "do not predict a product for a drawing request. "
                    "also provide reactant/product names so the service can independently "
                    "resolve and validate them. If the user names reactants/products but you "
                    "are unsure of a reaction SMILES, leave reaction empty and provide "
                    "reactants/products names for validation. Represent elemental gases "
                    "and halogens through resolved participant names rather than generated "
                    "single atoms or radicals. Do not add byproducts or stoichiometric "
                    "balancing products unless they are explicitly supplied by the user. "
                    "For synthesis-route drawing, provide 1-4 candidate reaction SMILES steps "
                    "for the requested target when safe and high-confidence; include reactant "
                    "and product names for every step. Use conditions only for short "
                    "non-operational labels explicitly supplied by the user; do not infer "
                    "detailed lab conditions or provide operational recipes. "
                    "Do not use fixed templates, keyword routing, or memorized special cases; "
                    "use chemical reasoning and named structure resolution. "
                    "If the user request contains an active chemistry context section from a "
                    "previous turn, use that context to resolve pronouns and follow-up requests "
                    "instead of treating words like it/this/它/继续 as standalone molecules. "
                    "If uncertain, set kind=unsupported or requires_input=true."
                ),
            },
            {"role": "user", "content": query},
        ],
    )
    return parsed if isinstance(parsed, dict) else None


def _repair_studio_request_with_llm(
    *,
    query: str,
    failed_plan: dict[str, Any],
    failure_reason: str,
    llm_timeout: float = 30.0,
) -> dict[str, Any] | None:
    """Ask the model to repair an unexecutable canvas plan."""
    parsed, _settings = post_chemistry_llm_json(
        mode="smart",
        temperature=0.0,
        max_tokens=900,
        timeout=llm_timeout,
        messages=[
            {
                "role": "system",
                "content": (
                    "You repair Chemistry Studio canvas plans. Return strict JSON only with "
                    "schema {\"kind\":\"molecule|reaction|synthesis_route|unsupported\","
                    "\"reply\":\"\",\"target_name\":\"\",\"smiles\":\"\",\"reaction\":\"\","
                    "\"reactants\":[{\"name\":\"\",\"smiles\":\"\"}],"
                    "\"products\":[{\"name\":\"\",\"smiles\":\"\"}],"
                    "\"steps\":[{\"reaction\":\"A.B>>C\",\"reactants\":[{\"name\":\"\",\"smiles\":\"\"}],"
                    "\"products\":[{\"name\":\"\",\"smiles\":\"\"}],\"conditions\":\"\",\"note\":\"\"}],"
                    "\"pubchem_lookup\":\"\",\"requires_input\":false,\"confidence\":0.0}. "
                    "The previous plan failed validation or produced no drawable structure. "
                    "Re-read the original request and infer the drawable chemistry target using "
                    "model understanding, including Chinese compound names. "
                    "For a molecule, return a valid SMILES or a target_name/pubchem_lookup; when "
                    "you return a SMILES, also include target_name/pubchem_lookup for independent "
                    "verification. Preserve locants, stereochemistry, salts/charges, isotopes, "
                    "tautomer/protonation state, and fused-ring details. Do not repair by "
                    "simplifying to a common parent scaffold. "
                    "For a reaction or route, provide participant names and SMILES only when "
                    "the original request explicitly supports those participants; the service "
                    "will independently resolve and validate them. Represent elemental gases "
                    "and halogens through resolved participant names, not generated single "
                    "atoms. Do not add balancing byproducts for underspecified reaction drawings. "
                    "Do not write fixed templates, keyword shortcuts, lab "
                    "procedures, inferred conditions, yields, or unsupported certainty. "
                    "If the request is genuinely under-specified, set requires_input=true."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "original_request": query,
                        "failed_plan": failed_plan,
                        "failure_reason": failure_reason,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )
    return parsed if isinstance(parsed, dict) else None


def _payload_has_ketcher_load(payload: dict[str, Any]) -> bool:
    commands = ketcher_commands_from_payload(payload)
    return any(
        isinstance(command, dict)
        and str(command.get("type") or "") in KETCHER_STRUCTURE_COMMAND_TYPES
        for command in commands
    )


def _payload_failure_reason(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return "no payload"
    if payload.get("success") and _payload_has_ketcher_load(payload):
        return ""
    parts: list[str] = []
    for key in ("reply", "error"):
        value = str(payload.get(key) or "").strip()
        if value:
            parts.append(value)
    analysis = payload.get("analysis")
    if isinstance(analysis, dict):
        for key in ("resolution_error", "kind", "route_generation"):
            value = str(analysis.get(key) or "").strip()
            if value:
                parts.append(f"{key}: {value}")
    warnings = payload.get("warnings")
    if isinstance(warnings, list):
        parts.extend(str(item) for item in warnings[:3] if str(item or "").strip())
    return " | ".join(parts)[:700] or "no executable KetcherCommand"


def _annotation_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = [_annotation_text(item) for item in value]
        return "; ".join(part for part in parts if part)
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            text = _annotation_text(item)
            if text:
                parts.append(f"{str(key).strip()}: {text}")
        return "; ".join(parts)
    return re.sub(r"\s+", " ", str(value)).strip()


def _reaction_annotation_items(
    item: dict[str, Any] | None,
    *,
    note: str = "",
) -> list[dict[str, str]]:
    if not isinstance(item, dict):
        item = {}

    candidates = [
        ("Conditions", item.get("conditions") or item.get("condition")),
        ("Reagents", item.get("reagents") or item.get("reagent")),
        ("Catalyst", item.get("catalyst")),
        ("Solvent", item.get("solvent")),
        ("Temperature", item.get("temperature")),
        ("Note", note or item.get("note") or item.get("description")),
    ]
    annotations: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for label, raw_value in candidates:
        value = _annotation_text(raw_value)
        if not value:
            continue
        value = value[:220]
        key = (label, value)
        if key in seen:
            continue
        seen.add(key)
        annotations.append({"label": label, "value": value})
    return annotations


def _merge_reaction_annotations(
    *groups: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    annotations: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        if not isinstance(group, list):
            continue
        for item in group:
            if not isinstance(item, dict):
                continue
            label = _annotation_text(item.get("label")) or "Conditions"
            value = _annotation_text(item.get("value"))
            if label.lower() in {"conditions", "condition", "temperature", "temp"}:
                value = _canonical_reaction_condition(value)
            if not value:
                continue
            key = (label.lower(), value.lower())
            if key in seen:
                continue
            seen.add(key)
            annotations.append({"label": label[:80], "value": value[:220]})
    return annotations


def _canonical_reaction_condition(value: str) -> str:
    text = _annotation_text(value).strip(" ,，")
    text = re.sub(r"^[△Δ]\s*", "", text).strip(" ,，")
    lower = text.lower()
    if lower in {"heating", "heated"}:
        return "heat"
    if lower in {"refluxing", "refluxed"}:
        return "reflux"
    return text


def _extract_user_reaction_annotations(raw_query: str) -> list[dict[str, str]]:
    text = str(raw_query or "")
    field_patterns = [
        ("Conditions", r"(?:反应条件|条件|conditions?|condition)\s*(?:[:：=]|为|是)\s*([^\n。；;]+)"),
        ("Reagents", r"(?:试剂|reagents?|reagent)\s*(?:[:：=]|为|是)\s*([^\n。；;]+)"),
        ("Catalyst", r"(?:催化剂|catalysts?|catalyst)\s*(?:[:：=]|为|是)\s*([^\n。；;]+)"),
        ("Solvent", r"(?:溶剂|solvents?|solvent)\s*(?:[:：=]|为|是)\s*([^\n。；;]+)"),
        ("Temperature", r"(?:温度|temperatures?|temperature|temp)\s*(?:[:：=]|为|是)\s*([^\n。；;]+)"),
    ]
    short_condition_patterns = [
        r"\b(?:with|under)\s+(heat|heating|reflux)\b",
        r"\b(heat|heating|heated|reflux|refluxing|refluxed)\b",
        r"(加热|回流|升温|高温|室温|冷却|冰浴|光照)",
    ]
    annotations: list[dict[str, str]] = []
    for label, pattern in field_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = _canonical_reaction_condition(match.group(1))
        if not value:
            continue
        annotations.append({"label": label, "value": value[:220]})
    for pattern in short_condition_patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = _canonical_reaction_condition(match.group(1))
            if value:
                annotations.append({"label": "Conditions", "value": value[:220]})
    return _merge_reaction_annotations(annotations)


def _reaction_payload_annotations(
    route_steps: list[dict[str, Any]] | None,
    annotations: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    groups: list[list[dict[str, str]] | None] = [annotations]
    if route_steps:
        for step in route_steps:
            step_annotations = step.get("annotations") if isinstance(step, dict) else None
            groups.append(step_annotations if isinstance(step_annotations, list) else None)
    return _merge_reaction_annotations(*groups)


def _reaction_ketcher_command(
    *,
    reaction: str,
    rxnblock: str,
    title: str = "",
    step_index: int | None = None,
    annotations: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    command: dict[str, Any] = {
        "type": "load_reaction",
        "reaction": reaction,
        "reaction_smiles": reaction,
        "rxnfile": rxnblock,
        "rxnblock": rxnblock,
    }
    if title:
        command["title"] = title
    if step_index is not None:
        command["step_index"] = step_index
    if annotations:
        command["annotations"] = annotations
    return command


def _reaction_payload(
    *,
    reaction: str,
    route_name: str,
    reply: str,
    current_structure: dict[str, Any] | None = None,
    extra_analysis: dict[str, Any] | None = None,
    route_steps: list[dict[str, Any]] | None = None,
    annotations: list[dict[str, str]] | None = None,
    source: str = "llm_canvas_planner",
) -> dict[str, Any]:
    rxnblock = _rxnblock_from_reaction_smiles(reaction)
    analysis: dict[str, Any] = {
        "primary_tool": "chemistry_prepare_studio",
        "kind": "reaction",
        "route": route_name,
        "reaction": reaction,
        "source": source,
    }
    if route_steps:
        analysis["route_steps"] = route_steps
    if extra_analysis:
        analysis.update(extra_analysis)

    ketcher_commands: list[dict[str, Any]] = [{"type": "open_editor"}]
    if route_steps:
        for index, step in enumerate(route_steps, start=1):
            step_reaction = str(step.get("reaction") or "").strip()
            if not step_reaction:
                continue
            step_rxnblock = _rxnblock_from_reaction_smiles(step_reaction)
            step_annotations = step.get("annotations")
            ketcher_commands.append(
                _reaction_ketcher_command(
                    reaction=step_reaction,
                    rxnblock=step_rxnblock,
                    title=f"Route step {index}",
                    step_index=index,
                    annotations=step_annotations
                    if isinstance(step_annotations, list)
                    else None,
                )
            )
    if len(ketcher_commands) == 1:
        ketcher_commands.append(
            _reaction_ketcher_command(
                reaction=reaction,
                rxnblock=rxnblock,
                title=route_name.replace("_", " ").title(),
                annotations=annotations,
            )
        )

    payload_annotations = _reaction_payload_annotations(route_steps, annotations)
    payload: dict[str, Any] = {
        "success": True,
        "version": "2.0",
        "intent": "draw_reaction",
        "mode": "studio_prepare",
        "reply": reply,
        "ketcher_commands": ketcher_commands,
        "current_structure": current_structure,
        "analysis": analysis,
        "warnings": [],
    }
    if payload_annotations:
        payload["annotations"] = payload_annotations
    if route_steps:
        payload["route_state"] = {
            "available": True,
            "total_steps": len(route_steps),
            "current_step": 1,
        }
    return payload


def _molecule_payload(
    *,
    smiles: str,
    reply: str,
    analysis: dict[str, Any],
) -> dict[str, Any]:
    structure_summary = _structure_summary_from_smiles(smiles)
    if not structure_summary:
        return {
            "success": False,
            "version": "2.0",
            "intent": "draw_molecule",
            "mode": "studio_prepare",
            "requires_input": True,
            "reply": "The LLM plan did not produce a valid molecule structure.",
            "ketcher_commands": [],
            "current_structure": None,
            "analysis": {
                "primary_tool": "chemistry_prepare_studio",
                "kind": "molecule",
                "source": "llm_canvas_planner",
            },
            "warnings": ["Provide a SMILES string, CAS number, or clearer molecule name."],
        }

    molblock = str(structure_summary.get("molblock") or "")
    return {
        "success": True,
        "version": "2.0",
        "intent": "draw_molecule",
        "mode": "studio_prepare",
        "reply": reply or "Molecule prepared for Chemistry Studio.",
        "ketcher_commands": [
            {"type": "open_editor"},
            {
                "type": "load_molecule",
                "target": "ketcher",
                "smiles": structure_summary["canonical_smiles"],
                "molfile": molblock,
                "molblock": molblock,
            },
        ],
        "current_structure": structure_summary,
        "analysis": {
            "primary_tool": "chemistry_prepare_studio",
            "kind": "molecule",
            "source": "llm_canvas_planner",
            **analysis,
        },
        "warnings": [],
    }


def _resolve_planned_molecule(
    plan: dict[str, Any],
    raw_query: str,
    *,
    allow_pubchem: bool,
    lookup_timeout: float = 10.0,
) -> tuple[str, dict[str, Any]]:
    raw_smiles = str(plan.get("smiles") or "").strip()
    canonical = _canonicalize_smiles(raw_smiles)
    if canonical:
        target = _planned_target_lookup(plan)
        if allow_pubchem and target:
            verification = _resolve_target_with_external_name_services(target, timeout=lookup_timeout)
            if not verification.get("success"):
                verification = build_structure_resolution_payload(
                    target,
                    allow_pubchem=allow_pubchem,
                    timeout=lookup_timeout,
                )
            verified_smiles = str(verification.get("canonical_smiles") or "").strip()
            if verification.get("success") and verified_smiles:
                if _same_molecule_connectivity(canonical, verified_smiles):
                    verification_source = str(verification.get("source") or "")
                    return verified_smiles, {
                        "resolution_source": verification_source
                        or "structure_verification",
                        "resolved_name": verification.get("resolved_name") or target,
                        "confidence": verification.get("confidence"),
                        "llm_smiles_consistency_checked": True,
                        "llm_smiles_cross_checked": verification_source
                        in {"llm_guided_pubchem", "llm_guided_opsin"},
                    }
                return "", {
                    "resolution_source": "llm_smiles_conflict",
                    "resolved_name": verification.get("resolved_name") or target,
                    "resolution_error": (
                        "The LLM SMILES did not match the independently resolved target structure."
                    ),
                    "llm_smiles": canonical,
                    "verified_smiles": verified_smiles,
                    "verification_source": verification.get("source") or "",
                }
            if verification.get("source") or verification.get("error"):
                return canonical, {
                    "resolution_source": "llm_smiles_unverified",
                    "verification_source": verification.get("source") or "",
                    "verification_error": verification.get("error") or "",
                }
        return canonical, {"resolution_source": "llm_smiles"}

    target = str(
        _planned_target_lookup(plan)
        or raw_query
    ).strip()
    if allow_pubchem and target:
        external_resolution = _resolve_target_with_external_name_services(target, timeout=lookup_timeout)
        resolved_smiles = str(external_resolution.get("canonical_smiles") or "").strip()
        if external_resolution.get("success") and resolved_smiles:
            return resolved_smiles, {
                "resolution_source": external_resolution.get("source")
                or "external_name_to_structure",
                "resolved_name": external_resolution.get("resolved_name") or target,
                "confidence": external_resolution.get("confidence"),
            }

    resolution = build_structure_resolution_payload(
        target,
        allow_pubchem=allow_pubchem,
        timeout=lookup_timeout,
    )
    resolved_smiles = str(resolution.get("canonical_smiles") or "").strip()
    if resolution.get("success") and resolved_smiles:
        return resolved_smiles, {
            "resolution_source": resolution.get("source") or "llm_structure_resolution",
            "resolved_name": resolution.get("resolved_name") or target,
            "confidence": resolution.get("confidence"),
        }
    return "", {
        "resolution_source": resolution.get("source") or "llm_unresolved",
        "resolution_error": resolution.get("error") or "No molecule resolved",
    }


def _valid_route_steps(
    raw_steps: Any,
    *,
    allow_pubchem: bool,
    raw_query: str = "",
    lookup_timeout: float = 10.0,
    llm_timeout: float = 30.0,
) -> list[dict[str, Any]]:
    if not isinstance(raw_steps, list):
        return []

    steps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_steps[:8]:
        if not isinstance(item, dict):
            continue
        has_planned_participants = bool(
            _participant_entries(item.get("reactants"))
            or _participant_entries(item.get("products"))
        )
        raw_reaction = _canonicalize_reaction_smiles(
            str(item.get("reaction") or item.get("reaction_smiles") or "")
        )
        note = str(item.get("note") or item.get("description") or "").strip()
        validation_item = item
        participant_reaction, participant_resolution = _reaction_from_planned_participants(
            item,
            allow_pubchem=allow_pubchem,
            lookup_timeout=lookup_timeout,
        )
        if not participant_reaction and raw_reaction and raw_query:
            participant_plan = _extract_reaction_participants_with_llm(
                raw_query=raw_query,
                reaction=raw_reaction,
                note=note,
                llm_timeout=llm_timeout,
            )
            if participant_plan:
                participant_reaction, participant_resolution = _reaction_from_planned_participants(
                    participant_plan,
                    allow_pubchem=allow_pubchem,
                    lookup_timeout=lookup_timeout,
                )
                has_planned_participants = True
                validation_item = participant_plan
        if has_planned_participants and participant_resolution and not participant_reaction:
            continue
        reaction = participant_reaction or raw_reaction
        if not reaction or reaction in seen:
            continue
        if _reaction_has_generated_single_atom_element(reaction):
            continue
        seen.add(reaction)
        reactant_entries = _participant_entries(validation_item.get("reactants"))
        product_entries = _participant_entries(validation_item.get("products"))
        if participant_resolution:
            reactant_entries = _participant_entries_with_resolution(
                reactant_entries,
                participant_resolution,
                "reactant",
            )
            product_entries = _participant_entries_with_resolution(
                product_entries,
                participant_resolution,
                "product",
            )
        step_record: dict[str, Any] = {
            "reaction": reaction,
            "note": note,
            "annotations": _reaction_annotation_items(validation_item, note=note),
            "source": "llm_canvas_planner",
            "reactants": reactant_entries,
            "products": product_entries,
        }
        if participant_resolution:
            step_record["participant_resolution"] = participant_resolution
        if participant_reaction and raw_reaction and participant_reaction != raw_reaction:
            step_record["reaction_repaired_from_participants"] = True
        steps.append(step_record)
        if len(steps) >= 4:
            break
    return steps


def _validate_generated_reaction_for_canvas(
    *,
    reaction: str,
    plan: dict[str, Any],
    raw_query: str,
    confidence: float | None = None,
    require_product_language: bool = True,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Apply the single drawable-reaction contract for all LLM-generated routes.

    The LLM may propose chemistry, but Ketcher only receives a reaction when the
    generated components are bound to user-supported participant evidence and
    the product identity is explicit. Explicit user-supplied reaction SMILES
    bypass this function earlier in the request path and are preserved as input.
    """
    if _reaction_has_generated_single_atom_element(reaction):
        return (
            _reaction_guardrail_payload(
                raw_query=raw_query,
                reply="",
                confidence=confidence,
                guardrail="invalid_generated_elemental_species",
                warning=(
                    "Reaction drawing is blocked because the generated reaction "
                    "contains a single-atom elemental component instead of a "
                    "resolved participant molecule."
                ),
            ),
            {},
        )

    component_evidence = _reaction_component_evidence_report(
        reaction=reaction,
        plan=plan,
        raw_query=raw_query,
    )
    if not component_evidence.get("supported"):
        payload = _reaction_guardrail_payload(
            raw_query=raw_query,
            reply="",
            confidence=confidence,
            guardrail="unsupported_reaction_components",
            warning=(
                "Reaction drawing is blocked because one or more generated "
                "components were not bound to evidence from the user request."
            ),
        )
        if isinstance(payload.get("analysis"), dict):
            payload["analysis"]["component_evidence"] = component_evidence
        return payload, component_evidence

    if not _query_mentions_reaction_product(
        reaction=reaction,
        plan=plan,
        raw_query=raw_query,
        require_product_language=require_product_language,
    ):
        return (
            _reaction_guardrail_payload(
                raw_query=raw_query,
                reply="",
                confidence=confidence,
            ),
            component_evidence,
        )

    return None, component_evidence


def _payload_from_single_studio_plan(
    *,
    plan: dict[str, Any],
    raw_query: str,
    allow_pubchem: bool,
    lookup_timeout: float = 10.0,
    llm_timeout: float = 30.0,
) -> dict[str, Any]:
    """Convert one LLM plan into a validated drawable payload without retrying."""
    kind = str(plan.get("kind") or "").strip().lower()
    reply = str(plan.get("reply") or "").strip()
    confidence_raw = plan.get("confidence")
    confidence = (
        round(float(confidence_raw), 3)
        if isinstance(confidence_raw, (int, float))
        else None
    )
    planner_requires_input = bool(plan.get("requires_input"))
    low_confidence = confidence is not None and confidence < 0.7
    if planner_requires_input or low_confidence:
        intent = {
            "molecule": "draw_molecule",
            "reaction": "draw_reaction",
            "synthesis_route": "draw_reaction",
        }.get(kind, "prepare_chemistry_studio")
        warnings = ["The model did not provide a high-confidence drawable plan."]
        if kind == "molecule":
            warnings.append("Provide a SMILES string, CAS number, or more specific molecule name.")
        elif kind in {"reaction", "synthesis_route"}:
            warnings.append("Provide complete reactants and products, or a more specific target.")
        return {
            "success": False,
            "version": "2.0",
            "intent": intent,
            "mode": "studio_prepare",
            "requires_input": True,
            "reply": reply or "I need a more specific chemistry target before drawing.",
            "ketcher_commands": [],
            "current_structure": None,
            "analysis": {
                "primary_tool": "chemistry_prepare_studio",
                "kind": kind or "unsupported",
                "source": "llm_canvas_planner",
                "planner_confidence": confidence,
                "planner_requires_input": planner_requires_input,
            },
            "warnings": warnings,
        }

    if kind == "molecule":
        smiles, analysis = _resolve_planned_molecule(
            plan,
            raw_query,
            allow_pubchem=allow_pubchem,
            lookup_timeout=lookup_timeout,
        )
        if not smiles:
            return {
                "success": False,
                "version": "2.0",
                "intent": "draw_molecule",
                "mode": "studio_prepare",
                "requires_input": True,
                "reply": reply or "I could not resolve the requested molecule.",
                "ketcher_commands": [],
                "current_structure": None,
                "analysis": {
                    "primary_tool": "chemistry_prepare_studio",
                    "kind": "molecule",
                    "source": "llm_canvas_planner",
                    **analysis,
                },
                "warnings": ["Provide a SMILES string, CAS number, or clearer molecule name."],
            }
        if confidence is not None:
            analysis["planner_confidence"] = confidence
        return _molecule_payload(smiles=smiles, reply=reply, analysis=analysis)

    if kind == "reaction":
        steps = _valid_route_steps(
            [plan],
            allow_pubchem=allow_pubchem,
            raw_query=raw_query,
            lookup_timeout=lookup_timeout,
            llm_timeout=llm_timeout,
        )
        if not steps:
            steps = _valid_route_steps(
                plan.get("steps"),
                allow_pubchem=allow_pubchem,
                raw_query=raw_query,
                lookup_timeout=lookup_timeout,
                llm_timeout=llm_timeout,
            )
        reaction = steps[0]["reaction"] if steps else ""
        if not reaction:
            reaction = _canonicalize_reaction_smiles(str(plan.get("reaction") or ""))
        if not reaction:
            return {
                "success": False,
                "version": "2.0",
                "intent": "draw_reaction",
                "mode": "studio_prepare",
                "requires_input": True,
                "reply": reply or "I could not resolve a complete reaction for Chemistry Studio.",
                "ketcher_commands": [],
                "current_structure": None,
                "analysis": {
                    "primary_tool": "chemistry_prepare_studio",
                    "kind": "reaction",
                    "source": "llm_canvas_planner",
                },
                "warnings": [
                    "Provide complete reactants and products, or ask for a molecule instead."
                ],
            }
        guardrail_payload, component_evidence = _validate_generated_reaction_for_canvas(
            reaction=reaction,
            plan=plan,
            raw_query=raw_query,
            confidence=confidence,
        )
        if guardrail_payload is not None:
            if reply and guardrail_payload.get("analysis", {}).get("guardrail") == "missing_user_supported_reaction_product":
                guardrail_payload["reply"] = reply
            return guardrail_payload
        product_summary = _structure_summary_from_smiles(reaction.split(">>", 1)[1].split(".")[0])
        extra_analysis: dict[str, Any] = {}
        if steps:
            extra_analysis["participant_resolution"] = steps[0].get("participant_resolution")
            extra_analysis["reaction_repaired_from_participants"] = bool(
                steps[0].get("reaction_repaired_from_participants")
            )
        annotations = (
            steps[0].get("annotations")
            if steps and isinstance(steps[0].get("annotations"), list)
            else _reaction_annotation_items(
                plan,
                note=str(plan.get("note") or "").strip(),
            )
        )
        annotations = _merge_reaction_annotations(
            annotations,
            _extract_user_reaction_annotations(raw_query),
        )
        extra_analysis["component_evidence"] = component_evidence
        if confidence is not None:
            extra_analysis["planner_confidence"] = confidence
        return _reaction_payload(
            reaction=reaction,
            route_name="llm_planned_reaction",
            reply=reply or "Reaction draft prepared for Chemistry Studio.",
            current_structure=product_summary,
            extra_analysis=extra_analysis,
            annotations=annotations,
        )

    if kind == "synthesis_route":
        route_steps = _valid_route_steps(
            plan.get("steps"),
            allow_pubchem=allow_pubchem,
            raw_query=raw_query,
            lookup_timeout=lookup_timeout,
            llm_timeout=llm_timeout,
        )
        if not route_steps:
            route_steps = _valid_route_steps(
                [plan],
                allow_pubchem=allow_pubchem,
                raw_query=raw_query,
                lookup_timeout=lookup_timeout,
                llm_timeout=llm_timeout,
            )
        if not route_steps:
            reaction = _canonicalize_reaction_smiles(str(plan.get("reaction") or ""))
            if reaction:
                route_steps = [
                    {
                        "reaction": reaction,
                        "note": str(plan.get("note") or "").strip(),
                        "annotations": _reaction_annotation_items(
                            plan,
                            note=str(plan.get("note") or "").strip(),
                        ),
                        "source": "llm_canvas_planner",
                    }
                ]
        user_annotations = _extract_user_reaction_annotations(raw_query)
        if user_annotations:
            for step in route_steps:
                if isinstance(step, dict):
                    step["annotations"] = _merge_reaction_annotations(
                        step.get("annotations")
                        if isinstance(step.get("annotations"), list)
                        else None,
                        user_annotations,
                    )
        if not route_steps:
            smiles, analysis = _resolve_planned_molecule(
                plan,
                raw_query,
                allow_pubchem=allow_pubchem,
                lookup_timeout=lookup_timeout,
            )
            if smiles:
                return _molecule_payload(
                    smiles=smiles,
                    reply=(
                        reply
                        or "The target molecule was prepared, but no validated route step was generated."
                    ),
                    analysis={
                        "route_generation": "no_validated_steps",
                        **analysis,
                    },
                )
            return {
                "success": False,
                "version": "2.0",
                "intent": "draw_reaction",
                "mode": "studio_prepare",
                "requires_input": True,
                "reply": reply or "I could not generate a validated synthesis route drawing.",
                "ketcher_commands": [],
                "current_structure": None,
                "analysis": {
                    "primary_tool": "chemistry_prepare_studio",
                    "kind": "synthesis_route",
                    "source": "llm_canvas_planner",
                },
                "warnings": [
                    "Provide a target SMILES or more specific precursor/product information."
                ],
            }

        first_step = route_steps[0]
        first_reaction = first_step["reaction"]
        guardrail_payload, component_evidence = _validate_generated_reaction_for_canvas(
            reaction=first_reaction,
            plan=first_step,
            raw_query=raw_query,
            confidence=confidence,
            require_product_language=False,
        )
        if guardrail_payload is not None:
            return guardrail_payload
        product_summary = _structure_summary_from_smiles(first_reaction.split(">>", 1)[1].split(".")[0])
        extra_analysis = {
            "route_generation": "llm_validated_steps",
            "component_evidence": component_evidence,
        }
        if confidence is not None:
            extra_analysis["planner_confidence"] = confidence
        return _reaction_payload(
            reaction=first_reaction,
            route_name="llm_planned_synthesis_route",
            reply=reply or "Candidate synthesis route prepared for Chemistry Studio.",
            current_structure=product_summary,
            extra_analysis=extra_analysis,
            route_steps=route_steps,
        )

    return {
        "success": False,
        "version": "2.0",
        "intent": "prepare_chemistry_studio",
        "mode": "studio_prepare",
        "requires_input": True,
        "reply": reply or "The LLM planner did not identify a drawable chemistry request.",
        "ketcher_commands": [],
        "warnings": [
            "Ask to draw a specific molecule, reaction, or synthesis route with enough context."
        ],
    }


def _build_studio_preparation_payload_impl(
    query: Any,
    *,
    allow_pubchem: bool = True,
    timeout: Any = 90.0,
) -> dict[str, Any]:
    """Return an LLM-planned chemistry payload that can open Ketcher."""
    raw_query = str(query or "").strip()
    try:
        timeout_budget = float(timeout)
    except (TypeError, ValueError):
        timeout_budget = 90.0
    timeout_budget = max(5.0, min(240.0, timeout_budget))
    lookup_timeout = max(1.0, min(15.0, timeout_budget / 6.0))
    llm_timeout = max(5.0, min(45.0, timeout_budget / 3.0))

    if not raw_query:
        return {
            "success": False,
            "version": "2.0",
            "intent": "prepare_chemistry_studio",
            "requires_input": True,
            "reply": "No molecule or reaction was provided.",
            "ketcher_commands": [],
            "warnings": ["Provide a compound name, SMILES string, or reaction request."],
        }

    user_request = _user_request_text(raw_query) or raw_query

    user_reaction = _extract_user_reaction_smiles(user_request)
    if user_reaction:
        product_summary = _structure_summary_from_smiles(
            user_reaction.split(">>", 1)[1].split(".")[0]
        )
        return _reaction_payload(
            reaction=user_reaction,
            route_name="input_reaction_smiles",
            reply="Reaction SMILES prepared for Chemistry Studio.",
            current_structure=product_summary,
            extra_analysis={
                "input_preserved": True,
                "reaction_source": "user_explicit_reaction_smiles",
            },
            annotations=_merge_reaction_annotations(
                _extract_user_reaction_annotations(user_request),
                _extract_user_reaction_annotations(raw_query),
            ),
            source="input_reaction_smiles",
        )

    known_molecule = extract_known_molecule(user_request)
    if known_molecule is not None and _is_direct_molecule_canvas_request(user_request):
        return _molecule_payload(
            smiles=known_molecule.canonical_smiles,
            reply="Molecule prepared for Chemistry Studio.",
            analysis={
                "source": "local_curated_alias",
                "resolution_source": "local_curated_alias",
                "resolved_name": known_molecule.canonical_name,
                "confidence": 1.0,
            },
        )

    plan = _plan_studio_request_with_llm(raw_query, llm_timeout=llm_timeout)
    if not plan:
        return {
            "success": False,
            "version": "2.0",
            "intent": "prepare_chemistry_studio",
            "mode": "studio_prepare",
            "source": "llm_unavailable",
            "requires_input": True,
            "reply": "LLM canvas planning is unavailable.",
            "ketcher_commands": [],
            "warnings": [
                "Configure CHEMISTRY_STUDIO_LLM_* or CHEMISTRY_COPILOT_LLM_* and retry."
            ],
        }

    payload = _payload_from_single_studio_plan(
        plan=plan,
        raw_query=user_request,
        allow_pubchem=allow_pubchem,
        lookup_timeout=lookup_timeout,
        llm_timeout=llm_timeout,
    )
    if payload.get("success") and _payload_has_ketcher_load(payload):
        return payload
    if _is_evidence_gate_payload(payload):
        return payload

    repair_plan = _repair_studio_request_with_llm(
        query=user_request,
        failed_plan=plan,
        failure_reason=_payload_failure_reason(payload),
        llm_timeout=llm_timeout,
    )
    if repair_plan:
        repaired_payload = _payload_from_single_studio_plan(
            plan=repair_plan,
            raw_query=user_request,
            allow_pubchem=allow_pubchem,
            lookup_timeout=lookup_timeout,
            llm_timeout=llm_timeout,
        )
        if repaired_payload.get("success") and _payload_has_ketcher_load(repaired_payload):
            repaired_payload.setdefault("analysis", {})
            if isinstance(repaired_payload.get("analysis"), dict):
                repaired_payload["analysis"]["repair_pass"] = "llm_replan"
                repaired_payload["analysis"]["first_plan_kind"] = str(plan.get("kind") or "")
            return repaired_payload

    return payload


def build_studio_preparation_payload(
    query: Any,
    *,
    allow_pubchem: bool = True,
    timeout: Any = 90.0,
) -> dict[str, Any]:
    """Return a canonical KetcherCommand payload for Chemistry Studio."""

    return with_ketcher_commands(
        _build_studio_preparation_payload_impl(
            query,
            allow_pubchem=allow_pubchem,
            timeout=timeout,
        )
    )


def prepare_studio(
    query: Any,
    allow_pubchem: Any = True,
    timeout: Any = 90.0,
) -> tuple[dict[str, Any], int]:
    """Return a Flask-ready `(payload, status_code)` tuple."""
    try:
        payload = build_studio_preparation_payload(
            query,
            allow_pubchem=bool(allow_pubchem),
            timeout=timeout,
        )
        status_code = 503 if payload.get("source") == "llm_unavailable" else 200
        return payload, status_code
    except Exception as exc:
        return {"error": str(exc), "success": False}, 500
