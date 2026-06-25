"""LLM-driven structure name and SMILES resolution for v2 chemistry."""

from __future__ import annotations

import re
import os
import threading
import time
from typing import Any, Dict, Tuple
from urllib.parse import quote

import requests
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, rdMolDescriptors

from gvim_v2.chemistry.known_molecules import extract_known_molecule, resolve_known_molecule
from gvim_v2.chemistry.llm_json import post_chemistry_llm_json


RDLogger.DisableLog("rdApp.error")

_SMILES_LABEL_RE = re.compile(
    r"(?i)\b(?:canonical\s+smiles|isomeric\s+smiles|smiles)\b\s*[:=]\s*([^\s,;]+)"
)
_SMILES_ALLOWED_RE = re.compile(r"^[A-Za-z0-9@+\-\[\]\(\)=#$\\/%.:]+$")
_PUBCHEM_RETRY_STATUSES = {429}
_PUBCHEM_USER_AGENT = os.environ.get("PUBCHEM_USER_AGENT", "GVIM-ChemistryStudio/2.1").strip() or "GVIM-ChemistryStudio/2.1"
_PUBCHEM_CACHE_TTL_SECONDS = 24 * 60 * 60
_PUBCHEM_MIN_INTERVAL_SECONDS = 0.25
_PUBCHEM_CACHE: dict[str, tuple[float, tuple[str, str]]] = {}
_PUBCHEM_LOCK = threading.Lock()
_PUBCHEM_LAST_REQUEST_TS = 0.0

_ACTION_PREFIX_RE = re.compile(
    r"(?ix)^\s*(?:"
    r"please|pls|kindly|can\s+you|could\s+you|"
    r"draw|sketch|open|load|show|display|render|resolve|lookup|find|analy[sz]e|"
    r"structure\s+of|molecule\s+of|compound\s+of|chemical\s+name\s*[:=]?|"
    r"name\s*[:=]?|compound\s*[:=]?|molecule\s*[:=]?|target\s*[:=]?|"
    r"请|帮我|麻烦|绘制|画出|画一下|打开|载入|加载|展示|显示|解析|查询|查找|分析"
    r")\s+"
)
_ACTION_TOKEN_RE = re.compile(
    r"(?ix)\b(?:"
    r"please|pls|kindly|draw|sketch|open|load|show|display|render|resolve|lookup|find|"
    r"analy[sz]e|structure|molecule|compound|chemical|name|target|in|on|into|with|for|"
    r"ketcher|canvas|editor|studio"
    r")\b"
)
_CJK_ACTION_TOKEN_RE = re.compile(
    r"(?:请|帮我|麻烦|在|中|里|把|将|绘制|画出|画一下|打开|载入|加载|展示|显示|解析|查询|查找|分析|"
    r"结构|分子|化合物|编辑器|画布)"
)
_LOOKUP_LABEL_RE = re.compile(
    r"(?ix)\b(?:compound|molecule|chemical|name|target|pubchem|cas)\b\s*[:=]\s*([^\n\r;]+)"
)


def _mol_from_smiles(value: str) -> Chem.Mol | None:
    cleaned = str(value or "").strip()
    if not cleaned or not _SMILES_ALLOWED_RE.fullmatch(cleaned):
        return None
    try:
        return Chem.MolFromSmiles(cleaned)
    except Exception:
        return None


def _canonicalize_smiles(value: str) -> str:
    mol = _mol_from_smiles(value)
    if mol is None:
        return ""
    return Chem.MolToSmiles(mol, canonical=True)


def _dedupe_preserve_order(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return tuple(ordered)


def _clean_lookup_candidate(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    text = text.strip(" \t\r\n\"'`“”‘’[]{}()<>")
    text = text.replace("：", ":").replace("，", ",").replace("。", " ")
    text = re.sub(r"\s+", " ", text)

    for _ in range(4):
        updated = _ACTION_PREFIX_RE.sub("", text).strip()
        if updated == text:
            break
        text = updated

    text = re.sub(r"(?i)\b(?:in|on|into)\s+(?:ketcher|canvas|editor|studio)\b", " ", text)
    text = _ACTION_TOKEN_RE.sub(" ", text)
    text = _CJK_ACTION_TOKEN_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" \t\r\n:：,，;；.。")
    return text


def iter_pubchem_lookup_candidates(value: Any) -> tuple[str, ...]:
    """Return deterministic PubChem lookup candidates extracted from user text."""
    raw = str(value or "").strip()
    if not raw:
        return ()

    known = resolve_known_molecule(raw) or extract_known_molecule(raw)
    if known is not None:
        return (known.canonical_name,)

    candidates: list[str] = []
    for match in _LOOKUP_LABEL_RE.finditer(raw):
        candidates.append(match.group(1))
    for match in re.finditer(r"[\"'`“”‘’]([^\"'`“”‘’]{2,160})[\"'`“”‘’]", raw):
        candidates.append(match.group(1))

    cleaned = _clean_lookup_candidate(raw)
    if cleaned:
        candidates.append(cleaned)
    candidates.append(raw)

    return _dedupe_preserve_order(candidates)


def _wait_for_pubchem_slot() -> None:
    global _PUBCHEM_LAST_REQUEST_TS
    with _PUBCHEM_LOCK:
        now = time.monotonic()
        wait_seconds = _PUBCHEM_MIN_INTERVAL_SECONDS - (now - _PUBCHEM_LAST_REQUEST_TS)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        _PUBCHEM_LAST_REQUEST_TS = time.monotonic()


def _retry_after_seconds(response: requests.Response) -> float | None:
    raw_value = str(response.headers.get("Retry-After") or "").strip()
    if not raw_value:
        return None
    try:
        return max(0.0, min(float(raw_value), 5.0))
    except ValueError:
        return None


def _payload_from_mol(
    *,
    query: str,
    mol: Chem.Mol,
    source: str,
    resolved_name: str | None = None,
    confidence: float = 1.0,
    warnings: list[str] | None = None,
) -> Dict[str, Any]:
    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    return {
        "success": True,
        "version": "2.0",
        "query": query,
        "source": source,
        "resolved_name": resolved_name or "",
        "confidence": confidence,
        "canonical_smiles": canonical_smiles,
        "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight": round(float(Descriptors.ExactMolWt(mol)), 4),
        "heavy_atom_count": int(mol.GetNumAtoms()),
        "warnings": warnings or [],
    }


def _iter_direct_smiles_candidates(value: Any) -> tuple[str, ...]:
    """Return only user-provided SMILES candidates, not name aliases."""
    raw = str(value or "").strip()
    if not raw:
        return ()

    candidates: list[str] = [raw]
    for match in _SMILES_LABEL_RE.finditer(raw):
        candidate = str(match.group(1) or "").strip()
        if candidate:
            candidates.append(candidate)

    deduped: list[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return tuple(deduped)


def _resolve_with_pubchem(name: str, timeout: float) -> tuple[str, str] | None:
    lookup = str(name or "").strip()
    if not lookup:
        return None

    if _mol_from_smiles(lookup) is not None:
        return None

    cache_key = lookup.casefold()
    now = time.monotonic()
    with _PUBCHEM_LOCK:
        cached = _PUBCHEM_CACHE.get(cache_key)
        if cached and now - cached[0] < _PUBCHEM_CACHE_TTL_SECONDS:
            return cached[1]

    endpoint = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        f"{quote(lookup)}/property/CanonicalSMILES,IsomericSMILES/JSON"
    )
    session = requests.Session()
    session.trust_env = False
    try:
        data = None
        for attempt in range(2):
            _wait_for_pubchem_slot()
            try:
                response = session.get(
                    endpoint,
                    headers={"User-Agent": _PUBCHEM_USER_AGENT},
                    timeout=timeout,
                )
            except requests.RequestException:
                if attempt < 1:
                    time.sleep(0.4 * (2 ** attempt))
                    continue
                return None
            if response.status_code == 200:
                data = response.json()
                break
            if response.status_code in _PUBCHEM_RETRY_STATUSES and attempt < 1:
                time.sleep(_retry_after_seconds(response) or (0.4 * (2 ** attempt)))
                continue
            return None
        if data is None:
            return None
    except Exception:
        return None
    finally:
        session.close()

    properties = ((data.get("PropertyTable") or {}).get("Properties") or [])
    first = properties[0] if properties else {}
    raw_smiles = str(
        first.get("IsomericSMILES")
        or first.get("CanonicalSMILES")
        or first.get("SMILES")
        or ""
    ).strip()
    if not raw_smiles:
        return None
    result = (raw_smiles, lookup)
    with _PUBCHEM_LOCK:
        _PUBCHEM_CACHE[cache_key] = (time.monotonic(), result)
    return result


def resolve_name_with_pubchem(query: Any, timeout: float = 10.0) -> tuple[str, str] | None:
    for lookup in iter_pubchem_lookup_candidates(query):
        hit = _resolve_with_pubchem(lookup, timeout=timeout)
        if hit is not None:
            return hit
    return None


def _resolve_with_opsin(name: str, timeout: float) -> tuple[str, str] | None:
    lookup = str(name or "").strip()
    if not lookup:
        return None

    endpoint = f"https://www.ebi.ac.uk/opsin/ws/{quote(lookup, safe='')}.json"
    session = requests.Session()
    session.trust_env = False
    try:
        response = session.get(endpoint, timeout=timeout)
        if response.status_code != 200:
            return None
        data = response.json()
    except Exception:
        return None
    finally:
        session.close()

    if str(data.get("status") or "").upper() != "SUCCESS":
        return None
    raw_smiles = str(data.get("smiles") or "").strip()
    if not raw_smiles:
        return None
    return raw_smiles, lookup


def resolve_name_with_external_services(query: Any, timeout: float = 10.0) -> tuple[str, str, str] | None:
    for lookup in iter_pubchem_lookup_candidates(query):
        pubchem_hit = _resolve_with_pubchem(lookup, timeout=timeout)
        if pubchem_hit is not None:
            smiles, name = pubchem_hit
            return "pubchem_name", smiles, name

        opsin_hit = _resolve_with_opsin(lookup, timeout=timeout)
        if opsin_hit is not None:
            smiles, name = opsin_hit
            return "opsin_name", smiles, name
    return None


def _resolve_structure_with_llm(query: str, *, timeout: float = 20.0) -> Dict[str, Any] | None:
    try:
        parsed, _settings = post_chemistry_llm_json(
            mode="smart",
            temperature=0.0,
            max_tokens=420,
            timeout=timeout,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a chemistry structure resolver. Return strict JSON only with "
                        "schema {\"kind\":\"molecule|not_molecule\","
                        "\"resolved_name\":\"\",\"smiles\":\"\",\"confidence\":0.0,"
                        "\"pubchem_lookup\":\"\",\"reason\":\"\"}. "
                        "Understand natural-language English and Chinese compound references. "
                        "If the user says draw/open/load/analyze a single named compound, extract "
                        "the compound identity and return kind=molecule. "
                        "For Chinese names, translate the compound identity to an English PubChem "
                        "lookup name in pubchem_lookup even when you are not fully certain of a "
                        "SMILES string. "
                        "For complex systematic names or descriptions, preserve locants, charge, "
                        "salt state, isotope, tautomer, E/Z, R/S, alpha/beta, and cis/trans details. "
                        "Do not simplify to a parent scaffold. If multiple structures are possible, "
                        "leave smiles empty and set pubchem_lookup/resolved_name for external "
                        "name-to-structure verification. "
                        "For a single molecule, return a high-confidence canonical or valid SMILES "
                        "when you know it; otherwise leave smiles empty and provide pubchem_lookup. "
                        "If the request is a reaction, synthesis route, unclear formula, or unsafe to "
                        "resolve confidently as one molecule, return kind=not_molecule and empty smiles. "
                        "Do not use named-reaction templates, reaction product guesses, or lab procedures."
                    ),
                },
                {"role": "user", "content": query},
            ],
        )
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def build_structure_resolution_payload(
    query: Any,
    *,
    allow_pubchem: bool = True,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Resolve a direct SMILES or LLM-understood molecule name to structure data."""
    raw_query = str(query or "").strip()
    if not raw_query:
        return {
            "success": False,
            "version": "2.0",
            "query": raw_query,
            "source": "unresolved",
            "confidence": 0.0,
            "error": "query is required",
            "warnings": [],
        }

    for candidate in _iter_direct_smiles_candidates(raw_query):
        direct_mol = _mol_from_smiles(candidate)
        if direct_mol is not None:
            return _payload_from_mol(
                query=raw_query,
                mol=direct_mol,
                source="input_smiles" if candidate == raw_query else "extracted_smiles",
                resolved_name="",
                confidence=1.0 if candidate == raw_query else 0.96,
            )

    known_molecule = resolve_known_molecule(raw_query) or extract_known_molecule(raw_query)
    if known_molecule is not None:
        mol = _mol_from_smiles(known_molecule.canonical_smiles)
        if mol is not None:
            return _payload_from_mol(
                query=raw_query,
                mol=mol,
                source="local_curated_alias",
                resolved_name=known_molecule.canonical_name,
                confidence=1.0,
            )

    direct_lookup_candidates = iter_pubchem_lookup_candidates(raw_query)
    should_try_direct_lookup = (
        bool(direct_lookup_candidates)
        and direct_lookup_candidates[0].casefold() != raw_query.casefold()
    )
    if allow_pubchem and should_try_direct_lookup and not re.search(r"[\u4e00-\u9fff]", raw_query):
        external_hit = resolve_name_with_external_services(raw_query, timeout=timeout)
        if external_hit is not None:
            source, smiles, name = external_hit
            mol = _mol_from_smiles(smiles)
            if mol is not None:
                return _payload_from_mol(
                    query=raw_query,
                    mol=mol,
                    source=source,
                    resolved_name=name,
                    confidence=0.9,
                )

    llm_timeout = max(5.0, min(30.0, float(timeout) * 2.0))
    llm_resolution = _resolve_structure_with_llm(raw_query, timeout=llm_timeout)
    if not llm_resolution:
        if allow_pubchem:
            external_hit = resolve_name_with_external_services(raw_query, timeout=timeout)
            if external_hit is not None:
                source, smiles, name = external_hit
                mol = _mol_from_smiles(smiles)
                if mol is not None:
                    return _payload_from_mol(
                        query=raw_query,
                        mol=mol,
                        source=source,
                        resolved_name=name,
                        confidence=0.86,
                    )
        return {
            "success": False,
            "version": "2.0",
            "query": raw_query,
            "source": "llm_unavailable",
            "confidence": 0.0,
            "error": "LLM structure resolution is unavailable",
            "warnings": [
                "Configure CHEMISTRY_STUDIO_LLM_* or CHEMISTRY_COPILOT_LLM_* and retry."
            ],
        }

    raw_confidence = llm_resolution.get("confidence")
    confidence = float(raw_confidence) if isinstance(raw_confidence, (int, float)) else 0.0
    raw_smiles = str(llm_resolution.get("smiles") or "").strip()
    resolved_name = str(llm_resolution.get("resolved_name") or "").strip()
    pubchem_lookup = str(llm_resolution.get("pubchem_lookup") or resolved_name).strip()

    if allow_pubchem and pubchem_lookup:
        pubchem_hit = _resolve_with_pubchem(pubchem_lookup, timeout=timeout)
        if pubchem_hit is not None:
            smiles, name = pubchem_hit
            mol = _mol_from_smiles(smiles)
            if mol is not None:
                return _payload_from_mol(
                    query=raw_query,
                    mol=mol,
                    source="llm_guided_pubchem",
                    resolved_name=name,
                    confidence=max(round(confidence, 3), 0.82),
                )
        opsin_hit = _resolve_with_opsin(pubchem_lookup, timeout=timeout)
        if opsin_hit is not None:
            smiles, name = opsin_hit
            mol = _mol_from_smiles(smiles)
            if mol is not None:
                return _payload_from_mol(
                    query=raw_query,
                    mol=mol,
                    source="llm_guided_opsin",
                    resolved_name=name,
                    confidence=max(round(confidence, 3), 0.84),
                )

    if str(llm_resolution.get("kind") or "").strip().lower() == "molecule" and confidence >= 0.7:
        mol = _mol_from_smiles(raw_smiles)
        if mol is not None:
            return _payload_from_mol(
                query=raw_query,
                mol=mol,
                source="llm_structure_resolution",
                resolved_name=resolved_name,
                confidence=round(confidence, 3),
                warnings=(
                    ["Structure accepted from LLM because no external name resolver hit was available."]
                    if pubchem_lookup
                    else []
                ),
            )

    return {
        "success": False,
        "version": "2.0",
        "query": raw_query,
        "source": "llm_unresolved",
        "confidence": round(confidence, 3),
        "error": "No molecule structure could be resolved from the LLM plan",
        "warnings": [
            "Try a SMILES string, CAS number, English compound name, or a more specific molecule name."
        ],
    }


def resolve_structure(
    query: Any,
    allow_pubchem: Any = True,
    timeout: Any = 10.0,
) -> Tuple[Dict[str, Any], int]:
    """Return a Flask-ready `(payload, status_code)` tuple."""
    try:
        timeout_value = float(timeout)
    except (TypeError, ValueError):
        timeout_value = 10.0
    timeout_value = max(1.0, min(30.0, timeout_value))

    payload = build_structure_resolution_payload(
        query=query,
        allow_pubchem=bool(allow_pubchem),
        timeout=timeout_value,
    )
    return payload, 200


__all__ = [
    "build_structure_resolution_payload",
    "iter_pubchem_lookup_candidates",
    "resolve_name_with_external_services",
    "resolve_name_with_pubchem",
    "resolve_structure",
    "_canonicalize_smiles",
]
