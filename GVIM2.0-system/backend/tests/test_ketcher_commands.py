from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "harness"))

from gvim_v2.chemistry.ketcher_commands import (  # noqa: E402
    first_structure_command,
    ketcher_commands_from_payload,
    normalize_ketcher_command,
    with_ketcher_commands,
)


def test_rejects_unknown_editor_commands():
    assert ketcher_commands_from_payload({"unknown_commands": [{"type": "load_ket"}]}) == []
    assert normalize_ketcher_command({"type": "toolbar_click", "id": "atom-carbon"}) is None
    assert normalize_ketcher_command({"type": "browser_coordinate_click", "x": 1, "y": 2}) is None


def test_reads_canonical_commands():
    payload = {
        "ketcher_commands": [{"type": "load_molecule", "smiles": "CCO"}],
    }

    assert ketcher_commands_from_payload(payload) == [
        {"type": "load_molecule", "smiles": "CCO"}
    ]
    assert first_structure_command(payload) == {"type": "load_molecule", "smiles": "CCO"}


def test_rejects_invalid_switch_mode_and_unknown_commands():
    assert normalize_ketcher_command({"type": "switch_mode", "mode": "bad"}) is None
    assert normalize_ketcher_command({"type": "toolbar_click", "id": "atom-carbon"}) is None


def test_with_ketcher_commands_preserves_single_output_contract():
    payload = {
        "success": True,
        "ketcher_commands": [{"type": "load_reaction", "reaction": "CCO>>CC=O"}],
    }

    output = with_ketcher_commands(payload)

    assert output["ketcher_command_contract"] == "1.0"
    assert output["ketcher_commands"] == [
        {"type": "load_reaction", "reaction": "CCO>>CC=O"}
    ]
