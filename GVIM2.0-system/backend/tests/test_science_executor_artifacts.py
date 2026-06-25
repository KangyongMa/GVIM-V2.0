from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("rdkit")
pytest.importorskip("pymatgen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "harness"))

from gvim_v2 import science_executor as se  # noqa: E402


def test_science_executor_declares_materials_artifacts(monkeypatch):
    def runner(args):
        return {
            "success": True,
            "source": "Materials Project",
            "results": [
                {
                    "material_id": "mp-149",
                    "formula_pretty": "Si",
                    "energy_above_hull_ev_atom": 0,
                }
            ],
        }

    tool_key = "test_materials_artifact"
    original = se.SCIENCE_TOOLS.get(tool_key)
    se.SCIENCE_TOOLS[tool_key] = se.ScienceTool(
        tool_key,
        "materials",
        "Test materials artifact declaration.",
        {},
        runner,
    )

    def planner(*, message, domain, context, mode):
        return (
            {
                "domain": "materials",
                "tool_key": tool_key,
                "tool_args": {},
                "requires_input": False,
                "missing_fields": [],
                "reply": "",
                "confidence": 1.0,
            },
            {"provider": "test", "model": "test"},
        )

    monkeypatch.setattr(se, "_plan_science_tool_with_llm", planner)

    try:
        payload, status = se.build_science_execution_payload("search Si in Materials Project")
    finally:
        if original is None:
            se.SCIENCE_TOOLS.pop(tool_key, None)
        else:
            se.SCIENCE_TOOLS[tool_key] = original

    assert status == 200
    assert payload["product_surface"] == "science_copilot"
    assert payload["science_artifacts"] == [
        {
            "kind": "materials",
            "title": f"Materials: {tool_key}",
            "tool_key": tool_key,
            "payload": payload["tool_result"],
        }
    ]


def test_science_artifact_declaration_prefers_3d_over_generic_materials():
    result = {
        "success": True,
        "source": "rdkit_native",
        "viewer": "3dmol",
        "canonical_smiles": "c1ccccc1",
        "molblock": "mol",
        "pdb_block": "pdb",
    }

    artifacts = se._science_artifacts_for_result("rdkit_3d_conformer", "chemistry", result)

    assert artifacts == [
        {
            "kind": "three-d",
            "title": "3D structure: c1ccccc1",
            "tool_key": "rdkit_3d_conformer",
            "payload": result,
        }
    ]


def test_science_executor_declares_ketcher_artifact_for_native_ket_action():
    ket = '{"root":{"nodes":[]}}'
    result = {
        "success": True,
        "ketcher_commands": [{"type": "load_ket", "ket": ket}],
        "current_structure": {},
    }

    artifacts = se._science_artifacts_for_result(
        "chemistry_studio_prepare",
        "chemistry",
        result,
    )

    assert artifacts == [
        {
            "kind": "ketcher",
            "title": "Ketcher structure",
            "tool_key": "chemistry_studio_prepare",
            "payload": {
                **result,
                "ketcher_command_contract": "1.0",
                "smiles": "",
                "molfile": "",
                "rxnblock": "",
                "ket": ket,
            },
        }
    ]


def test_science_capabilities_expose_verified_ketcher_commands():
    payload = se.build_science_capabilities_payload()
    commands = payload["chemistry_contract"]["ketcher_commands"]
    command_types = {command["type"] for command in commands}

    assert {
        "load_molecule",
        "load_reaction",
        "load_ket",
        "add_text",
        "layout",
        "set_zoom",
        "set_settings",
        "switch_mode",
        "clear",
    } <= command_types
    assert "toolbar_click" not in command_types
