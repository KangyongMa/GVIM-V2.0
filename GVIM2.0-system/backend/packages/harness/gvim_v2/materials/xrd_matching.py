"""Lightweight XRD peak matching utilities."""

from __future__ import annotations

from typing import Any


def _coerce_peak(value: Any) -> dict[str, float]:
    if isinstance(value, dict):
        position = value.get("two_theta", value.get("position", value.get("angle")))
        intensity = value.get("intensity", 1.0)
    else:
        position = value
        intensity = 1.0
    try:
        two_theta = float(position)
        peak_intensity = float(intensity)
    except (TypeError, ValueError) as exc:
        raise ValueError("peaks must be numbers or objects with two_theta/position") from exc
    if two_theta <= 0:
        raise ValueError("peak positions must be positive")
    return {"two_theta": two_theta, "intensity": peak_intensity}


def _coerce_peaks(values: Any, label: str) -> list[dict[str, float]]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{label} must be a non-empty list")
    if len(values) > 300:
        raise ValueError(f"{label} is limited to 300 peaks")
    return sorted((_coerce_peak(value) for value in values), key=lambda item: item["two_theta"])


def match_xrd_peaks(
    observed_peaks: Any,
    reference_peaks: Any,
    tolerance_two_theta: float = 0.25,
) -> dict[str, Any]:
    observed = _coerce_peaks(observed_peaks, "observed_peaks")
    reference = _coerce_peaks(reference_peaks, "reference_peaks")
    tolerance = float(tolerance_two_theta or 0.25)
    if tolerance <= 0 or tolerance > 2.0:
        raise ValueError("tolerance_two_theta must be between 0 and 2 degrees")

    used_observed: set[int] = set()
    matches: list[dict[str, float]] = []
    missing_reference: list[dict[str, float]] = []
    for ref_index, ref_peak in enumerate(reference):
        best_index: int | None = None
        best_delta = tolerance + 1.0
        for obs_index, obs_peak in enumerate(observed):
            if obs_index in used_observed:
                continue
            delta = abs(obs_peak["two_theta"] - ref_peak["two_theta"])
            if delta <= tolerance and delta < best_delta:
                best_delta = delta
                best_index = obs_index
        if best_index is None:
            missing_reference.append({"reference_index": ref_index, **ref_peak})
            continue
        used_observed.add(best_index)
        obs_peak = observed[best_index]
        matches.append(
            {
                "reference_index": ref_index,
                "observed_index": best_index,
                "reference_two_theta": ref_peak["two_theta"],
                "observed_two_theta": obs_peak["two_theta"],
                "delta_two_theta": round(obs_peak["two_theta"] - ref_peak["two_theta"], 6),
                "reference_intensity": ref_peak["intensity"],
                "observed_intensity": obs_peak["intensity"],
            }
        )

    extra_observed = [
        {"observed_index": index, **peak}
        for index, peak in enumerate(observed)
        if index not in used_observed
    ]
    recall = len(matches) / len(reference)
    precision = len(matches) / len(observed)
    score = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    has_high_precision_subset = precision >= 0.8 and len(matches) >= 3
    verdict = (
        "consistent"
        if score >= 0.75 and recall >= 0.7
        else "partial"
        if score >= 0.45 or has_high_precision_subset
        else "inconsistent"
    )
    return {
        "success": True,
        "version": "1.0",
        "source": "gvim_materials_xrd_peak_match",
        "tolerance_two_theta": tolerance,
        "score": round(score, 4),
        "match_score": round(score, 4),
        "match_count": len(matches),
        "unmatched_observed_count": len(extra_observed),
        "missing_reference_count": len(missing_reference),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "verdict": verdict,
        "matches": matches,
        "missing_reference_peaks": missing_reference,
        "extra_observed_peaks": extra_observed,
        "limitations": [
            "Peak-position matching is a fast triage step, not a full Rietveld refinement.",
            "Preferred orientation, strain, crystallite size, instrument calibration, and impurities can shift or suppress peaks.",
        ],
    }
