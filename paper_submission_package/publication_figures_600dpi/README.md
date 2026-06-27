# Publication Figures

This directory contains the high-resolution publication figures used by the
GVIM 2.0 manuscript. PNG and TIFF files are rendered at 600 DPI;
SVG files are retained for vector editing.

| Figure | Files | Data source | Reproduction script |
|---|---|---|---|
| Figure 2 | `Fig2_benchmark_performance.*` | `source_data_and_results/benchmark_400_raw_records/` and the Figure 2 source tables in `source_data_and_results/manuscript_source_data/` | `reproducibility_code/manuscript_and_figure_scripts/redraw_publication_figures.py` |
| Figure 3 | `Figure3_task_native_demos.*` | Front-end thread records and post-hoc public-gold scoring | `reproducibility_code/manuscript_and_figure_scripts/redraw_demo_landscape_figure.py` |
| Figure 4 | `Figure4_BACE_active_discovery.*` | `frontend_thread_records/fff9cae7-3467-496d-af05-0585c99fd993/` | `reproducibility_code/manuscript_and_figure_scripts/redraw_publication_figures.py` |
| Figure 5 | `Figure5_matbench_bandgap.*` | `frontend_thread_records/a6600dc1-8a72-46d1-97c0-d6ce0020c7f6/` | `reproducibility_code/manuscript_and_figure_scripts/redraw_true_main_case_figure.py` |
| Figure 6 | `Fig6_bace_temporal_external_validation.*` | `frontend_thread_records/9ae4e85f-542b-4f94-9294-81189cf220be/` | `reproducibility_code/manuscript_and_figure_scripts/draw_bace_temporal_publication_figure.py` |

Figure 5 uses the archived shuffled KFold workflow recorded by the front-end
thread, not official Matbench split semantics. Figure 6 is a label-withheld,
retrospective temporal public-data evaluation; it is not prospective or wet-lab
validation.

