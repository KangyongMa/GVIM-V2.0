# Packaging Notes

Created on 2026-06-25.

## Source roots

- System source: `E:\Demo of GVIM\deer-flow-mainnew\deer-flow-main`
- Paper submission package: `E:\Demo of GVIM\deer-flow-mainnew\GVIM2.0_Submission_Package_2026-06-22`
- Colab MCP source: `E:\Demo of GVIM\deer-flow-mainnew\colab-mcp-main`

## Inclusion policy

This package is intended for public code release and manuscript reproducibility. It therefore includes source code, configuration templates, scripts, source data, manuscript evidence, and reproducibility artifacts.

## Exclusion policy

Runtime state and secrets were excluded. In particular, `.env` and `.deer-flow` were not copied into `GVIM2.0-system/`.

Large model/data assets for selected public skills were excluded to keep the GitHub package uploadable on the available disk space. These assets are not the gold-standard evidence used by the GVIM 2.0 manuscript package.

The cleaned package also removes:

- `nmr_selected/`, a large local data directory not required for the GVIM 2.0 system startup path.
- `frontend/public/demo/`, static demo history not required for the manuscript evidence package.
- superseded manuscript drawing/editing helper scripts, keeping only final package, SI, and figure-generation scripts.
- intermediate SI render pages and the previous `GVIM2.0P.png` audit montage.

## Verification

The final release directory includes `RELEASE_FILE_MANIFEST.csv` and `ZIP_SHA256.txt`. The zip checksum is also written next to the zip file.
