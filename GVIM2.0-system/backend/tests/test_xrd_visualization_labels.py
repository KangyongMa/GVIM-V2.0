from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "harness"))

from gvim_v2.materials.structure_analysis import (  # noqa: E402
    _format_hkl_label,
    _select_xrd_annotation_indices,
)


def _peak(two_theta: float, intensity: float) -> dict[str, float]:
    return {"two_theta": two_theta, "intensity": intensity}


def test_format_hkl_label_is_compact_and_limits_multiple_families():
    label = _format_hkl_label(
        [
            {"hkl": [1, 1, 1], "multiplicity": 8},
            {"hkl": [2, 0, 0], "multiplicity": 6},
            {"hkl": [2, 2, 0], "multiplicity": 12},
        ]
    )

    assert label == "(111)+2"


def test_xrd_annotation_selection_limits_dense_patterns():
    peaks = [_peak(5 + index, 4.0) for index in range(90)]
    peaks[2]["intensity"] = 100.0
    peaks[10]["intensity"] = 70.0
    peaks[17]["intensity"] = 55.0
    peaks[28]["intensity"] = 35.0
    peaks[45]["intensity"] = 25.0
    peaks[70]["intensity"] = 20.0

    selected = _select_xrd_annotation_indices(peaks, max_annotations=12)

    assert len(selected) <= 12
    assert 2 in selected
    assert len(selected) < len(peaks)


def test_xrd_annotation_selection_avoids_adjacent_label_collisions():
    peaks = [
        _peak(20.0, 100.0),
        _peak(20.4, 95.0),
        _peak(20.8, 90.0),
        _peak(27.0, 50.0),
        _peak(34.0, 45.0),
        _peak(41.0, 40.0),
        _peak(55.0, 35.0),
    ]

    selected = _select_xrd_annotation_indices(peaks, max_annotations=6)

    assert 0 in selected
    assert not ({0, 1, 2} <= set(selected))
