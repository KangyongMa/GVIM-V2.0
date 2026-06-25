---
name: literature-parsing
description: Convert PDF literature to Markdown using MinerU API. GVIM/DeerFlow uses API mode by default, so the local mineru package is not required.
metadata:
  chemclaw:
    source: ChemClaw-main/skills/literature-parsing
    imported_as: deerflow-public-built-in
    triggers:
      - PDF to Markdown
      - convert PDF
      - literature parsing
      - extract figures
      - 解析文献
      - PDF 转 Markdown
---
# Literature Parsing

Convert a PDF paper to Markdown and keep a small metadata file for downstream DeerFlow workflows.

## GVIM API Mode

This skill calls MinerU through HTTP API, not through a local `mineru` command.

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
python scripts/literature_parsing.py -i paper.pdf -o ./output
python scripts/literature_parsing.py -i paper.pdf -o ./output -l en
python scripts/literature_parsing.py -i scanned.pdf -o ./output -m ocr
```

Output:

```text
output/
  paper/
    full.md
    full_metadata.json
```

In precise mode, extracted images may also be copied into `images/` when MinerU returns them in the result zip.
