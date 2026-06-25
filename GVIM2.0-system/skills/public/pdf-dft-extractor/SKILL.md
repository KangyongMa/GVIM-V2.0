---
name: pdf-dft-extractor
description: Extract DFT coordinate blocks from PDF supplementary information via MinerU API and generate Gaussian .gjf files.
metadata:
  chemclaw:
    source: ChemClaw-main/skills/pdf-dft-extractor
    imported_as: deerflow-public-built-in
    triggers:
      - DFT coordinates
      - Gaussian gjf
      - PDF DFT extractor
      - 提取 DFT 坐标
      - 生成 Gaussian 输入文件
---
# PDF DFT Extractor

Convert a PDF to Markdown through MinerU API, find DFT coordinate blocks, and generate Gaussian `.gjf` input files.

## GVIM API Mode

This skill calls MinerU through HTTP API; no local MinerU helper skill is required.

- Default mode: auto. If `MINERU_API_TOKEN` is set, use v4 precise API; otherwise use Agent API.
- Official Agent limits: 10 MB file size, 20 pages, Markdown output only.
- Optional precise mode: set `MINERU_API_MODE=precise` and `MINERU_API_TOKEN=<token>` to use MinerU v4 precise API.
- Required Python package in `gvims`: `requests`.

Environment variables:

```bash
MINERU_API_MODE=auto
MINERU_AGENT_API_BASE=https://mineru.net/api/v1/agent
MINERU_API_TIMEOUT_SECONDS=600
MINERU_API_POLL_SECONDS=3
```

Precise mode only:

```bash
MINERU_API_MODE=precise
MINERU_API_TOKEN=your_token
MINERU_API_MODEL=vlm
```

## Command Line

```bash
python extract_dft.py paper.pdf -o ./dft_output
python extract_dft.py ./pdfs -o ./dft_output --cpu 64 --mem 128GB
python extract_dft.py paper.pdf --method "B3LYP/6-31G(d)" --solvent "SMD(toluene)"
```

Output:

```text
dft_output/
  molecule_1.gjf
  molecule_2.gjf
  README.txt
```

Use `--keep-temp` when you need to inspect the Markdown returned by MinerU.
