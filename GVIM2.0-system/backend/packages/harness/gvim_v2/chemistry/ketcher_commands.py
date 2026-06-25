"""Canonical Ketcher command contract for native DeerFlow chemistry artifacts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

KETCHER_COMMAND_TYPES = {
    "open_editor",
    "load_molecule",
    "load_reaction",
    "load_ket",
    "add_text",
    "layout",
    "set_zoom",
    "set_settings",
    "switch_mode",
    "clear",
}

KETCHER_STRUCTURE_COMMAND_TYPES = {"load_molecule", "load_reaction", "load_ket"}

KETCHER_COMMANDS: list[dict[str, Any]] = [
    {
        "type": "open_editor",
        "description": "Render the embedded Ketcher editor.",
    },
    {
        "type": "load_molecule",
        "description": "Load a molecule from SMILES, Molfile, or MolBlock through Ketcher.setMolecule.",
        "fields": ["source", "smiles", "canonical_smiles", "molfile", "molblock", "value"],
    },
    {
        "type": "load_reaction",
        "description": "Load a reaction from an RDKit-validated RXN block or reaction SMILES through Ketcher.setMolecule.",
        "fields": ["rxnblock", "rxnfile", "reaction", "reaction_smiles", "value"],
    },
    {
        "type": "load_ket",
        "description": "Load native Ketcher KET JSON through Ketcher.setMolecule.",
        "fields": ["ket", "source", "value"],
    },
    {
        "type": "add_text",
        "description": "Add a native KET text object to the canvas.",
        "fields": ["content", "text", "value", "position", "x", "y", "z"],
    },
    {
        "type": "layout",
        "description": "Run Ketcher's native structure layout command.",
    },
    {
        "type": "set_zoom",
        "description": "Set Ketcher's editor zoom level.",
        "fields": ["zoom", "value"],
    },
    {
        "type": "set_settings",
        "description": "Apply Ketcher editor settings through Ketcher.setSettings.",
        "fields": ["settings"],
    },
    {
        "type": "switch_mode",
        "description": "Switch Ketcher between molecule and macromolecule editing modes.",
        "fields": ["mode"],
        "allowed_modes": ["molecules", "macromolecules"],
    },
    {
        "type": "clear",
        "description": "Clear the current Ketcher canvas.",
    },
]


def _string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _mode(value: Any) -> str:
    normalized = _string(value).lower()
    if normalized in {"molecule", "molecules"}:
        return "molecules"
    if normalized in {"macromolecule", "macromolecules", "sequence"}:
        return "macromolecules"
    return ""


def normalize_ketcher_command(raw: Any) -> dict[str, Any] | None:
    """Return one canonical command or None for unsupported input."""

    if not isinstance(raw, dict):
        return None

    command = deepcopy(raw)
    raw_type = _string(command.get("type"))
    if not raw_type:
        return None

    if raw_type not in KETCHER_COMMAND_TYPES:
        return None
    if raw_type == "switch_mode":
        mode = _mode(command.get("mode"))
        if not mode:
            return None
        command["mode"] = mode
    return command


def normalize_ketcher_commands(raw_commands: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_commands, list):
        return []
    commands: list[dict[str, Any]] = []
    for raw in raw_commands:
        command = normalize_ketcher_command(raw)
        if command is not None:
            commands.append(command)
    return commands


def ketcher_commands_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return normalize_ketcher_commands(payload.get("ketcher_commands"))


def first_structure_command(payload: dict[str, Any]) -> dict[str, Any]:
    for command in ketcher_commands_from_payload(payload):
        if _string(command.get("type")) in KETCHER_STRUCTURE_COMMAND_TYPES:
            return command
    return {}


def with_ketcher_commands(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach the canonical KetcherCommand contract."""

    output = deepcopy(payload)
    output["ketcher_command_contract"] = "1.0"
    output["ketcher_commands"] = ketcher_commands_from_payload(output)
    return output
