---
name: reaction-data-extraction
description: Extract chemistry reaction tables and reaction conditions from PDF literature using MinerU API plus rule-based parsing.
metadata:
  chemclaw:
    source: ChemClaw-main/skills/reaction-data-extraction
    imported_as: deerflow-public-built-in
    triggers:
      - reaction extraction
      - extract reaction conditions
      - reaction optimization
      - reaction table
      - 提取反应数据
      - 提取反应条件
---
# Reaction Data Extraction

Extract reaction-condition tables and likely free-text reaction conditions from chemistry PDFs, then write CSV or JSON.

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
python scripts/reaction_data_extraction.py -i paper.pdf -o ./output
python scripts/reaction_data_extraction.py -i paper.pdf -o ./output --tables-only
python scripts/reaction_data_extraction.py -i paper.pdf -o ./output --output-format json
python scripts/reaction_data_extraction.py -i ./papers -o ./output --batch
```

Output:

```text
output/
  paper/
    reaction_data.csv
    extraction_log.txt
    paper/
      full.md
      mineru_agent_result.json
```

The extractor is rule-based and intentionally lightweight. Optional packages such as `rdkit` or `chemdataextractor` can be installed for separate downstream chemistry analysis, but they are not required for the default API workflow.
