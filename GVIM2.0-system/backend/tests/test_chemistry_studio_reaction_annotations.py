from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("rdkit")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "harness"))

from gvim_v2.chemistry import studio_preparation as sp  # noqa: E402

REACTION_SMILES = (
    "C1=CCC=C1.O=C1C=CC(=O)O1>>O=C1OC(=O)C2C3C=CC(C3)C12"
)


def test_extracts_chinese_reaction_condition_with_copula():
    annotations = sp._extract_user_reaction_annotations("绘制D-A反应  反应条件为加热")

    assert annotations == [{"label": "Conditions", "value": "加热"}]


def test_explicit_reaction_smiles_preserves_english_heat_condition():
    payload = sp.build_studio_preparation_payload(
        f"{REACTION_SMILES} Diels-Alder reaction with heat",
        allow_pubchem=False,
        timeout=5,
    )

    assert payload["annotations"] == [{"label": "Conditions", "value": "heat"}]
    command = next(
        item for item in payload["ketcher_commands"] if item["type"] == "load_reaction"
    )
    assert command["annotations"] == [{"label": "Conditions", "value": "heat"}]


def test_explicit_reaction_smiles_preserves_chinese_heat_condition():
    payload = sp.build_studio_preparation_payload(
        f"{REACTION_SMILES} 反应条件为加热",
        allow_pubchem=False,
        timeout=5,
    )

    assert payload["annotations"] == [{"label": "Conditions", "value": "加热"}]


def test_reaction_annotation_merge_normalizes_triangle_heat_duplicates():
    annotations = sp._merge_reaction_annotations(
        [{"label": "Conditions", "value": "△ heat"}],
        [{"label": "Conditions", "value": "heat"}],
    )

    assert annotations == [{"label": "Conditions", "value": "heat"}]


def test_payload_has_ketcher_load_accepts_native_ket_command():
    assert sp._payload_has_ketcher_load(
        {"ketcher_commands": [{"type": "load_ket", "ket": '{"root":{"nodes":[]}}'}]}
    )
