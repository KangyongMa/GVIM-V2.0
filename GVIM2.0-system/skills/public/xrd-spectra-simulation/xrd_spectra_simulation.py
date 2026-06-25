#!/usr/bin/env python3
"""
XRD Spectrum from CIF

Input .cif structure file → calculate XRD pattern (Cu Kα) → save PNG.

Usage:
    python xrd_spectra_simulation.py 1100157.cif
    python xrd_spectra_simulation.py path/to/structure.cif --output /tmp/chemclaw/xrd.png

Outputs:
    - /tmp/chemclaw/xrd_spectrum.png
"""

import sys
import os
import argparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUTPUT_DIR = '/tmp/chemclaw'


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def format_hkl_label(hkl_items, max_terms=1):
    labels = []
    for item in hkl_items[:max(1, max_terms)]:
        hkl = item.get('hkl', ())
        if not hkl:
            continue
        labels.append('(' + ''.join(str(int(value)) for value in hkl) + ')')
    if not labels:
        return ''
    remaining = len(hkl_items) - len(labels)
    return ','.join(labels) + (f'+{remaining}' if remaining > 0 else '')


def select_annotation_indices(peaks, max_labels=12, min_relative_intensity=8.0):
    if not peaks or max_labels <= 0:
        return []
    first_angle = peaks[0]['two_theta']
    last_angle = peaks[-1]['two_theta']
    span = max(1.0, last_angle - first_angle)
    min_separation = max(1.5, span / 42.0)
    hard_limit = min(max_labels, len(peaks))
    required_floor = min(5, hard_limit)
    ranked = sorted(
        range(len(peaks)),
        key=lambda index: peaks[index]['intensity'],
        reverse=True,
    )
    selected = []

    def has_room(candidate_index, separation):
        candidate_angle = peaks[candidate_index]['two_theta']
        return all(
            abs(candidate_angle - peaks[selected_index]['two_theta']) >= separation
            for selected_index in selected
        )

    for index in ranked:
        if peaks[index]['intensity'] < min_relative_intensity and len(selected) >= required_floor:
            continue
        if has_room(index, min_separation):
            selected.append(index)
        if len(selected) >= hard_limit:
            break

    if len(selected) < required_floor:
        for index in ranked:
            if index in selected:
                continue
            if has_room(index, min_separation / 2):
                selected.append(index)
            if len(selected) >= required_floor:
                break
    return sorted(selected)


def plot_xrd_pattern(pattern, output_path, max_labels=12, label_min_intensity=8.0):
    peaks = [
        {
            'two_theta': float(two_theta),
            'intensity': float(intensity),
            'hkls': hkls,
            'label': format_hkl_label(hkls),
        }
        for two_theta, intensity, hkls in zip(pattern.x, pattern.y, pattern.hkls)
    ]
    annotation_indices = select_annotation_indices(
        peaks,
        max_labels=max_labels,
        min_relative_intensity=label_min_intensity,
    )

    fig, ax = plt.subplots(figsize=(10.5, 5.8), constrained_layout=True)
    for peak in peaks:
        ax.vlines(peak['two_theta'], 0, peak['intensity'], color='black', linewidth=1.2)

    for row, index in enumerate(annotation_indices):
        peak = peaks[index]
        if not peak['label']:
            continue
        y_offset = 2.5 + (row % 3) * 3.5
        ax.annotate(
            peak['label'],
            xy=(peak['two_theta'], peak['intensity']),
            xytext=(0, y_offset),
            textcoords='offset points',
            ha='center',
            va='bottom',
            rotation=90,
            fontsize=8,
            clip_on=False,
        )

    ax.set_xlabel('2theta (deg)')
    ax.set_ylabel('Intensity (scaled)')
    ax.set_ylim(0, 108)
    if peaks:
        ax.set_xlim(max(0, peaks[0]['two_theta'] - 2), peaks[-1]['two_theta'] + 2)
    ax.grid(axis='y', color='0.9', linewidth=0.8)
    fig.savefig(output_path, dpi=180, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description='XRD spectrum from CIF structure')
    parser.add_argument('cif', help='Path to .cif structure file')
    parser.add_argument('--output', default=os.path.join(OUTPUT_DIR, 'xrd_spectrum.png'), help='Output PNG path')
    parser.add_argument('--wavelength', default='CuKa', help='Radiation (CuKa, MoKa, etc.)')
    parser.add_argument('--max-labels', type=int, default=12, help='Maximum number of major peaks to annotate')
    parser.add_argument('--label-min-intensity', type=float, default=8.0, help='Minimum relative intensity for labels after the strongest peaks')
    args = parser.parse_args()

    if not os.path.exists(args.cif):
        print(f'Error: CIF file not found: {args.cif}')
        sys.exit(1)

    try:
        from pymatgen.core.structure import Structure
        from pymatgen.analysis.diffraction.xrd import XRDCalculator
    except ImportError:
        print('Error: pymatgen not installed. Run: pip install pymatgen')
        sys.exit(1)

    ensure_output_dir()
    print('=' * 60)
    print('XRD Spectrum Simulation')
    print('=' * 60)
    print(f'Loading: {args.cif}')
    structure = Structure.from_file(args.cif)
    print(f'  Formula: {structure.formula}')
    xrd_calc = XRDCalculator(wavelength=args.wavelength)
    pattern = xrd_calc.get_pattern(structure)
    plot_xrd_pattern(
        pattern,
        args.output,
        max_labels=max(0, args.max_labels),
        label_min_intensity=max(0.0, args.label_min_intensity),
    )
    print(f'Saved: {args.output}')
    print('=' * 60)


if __name__ == '__main__':
    main()
