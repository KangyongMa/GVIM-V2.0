from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path


RESEARCH_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = RESEARCH_ROOT.parent
DEMO_DIR = WORKSPACE_ROOT / "Demo-ChEMU"
RUNTIME_DIR = RESEARCH_ROOT / "showcase-information-extraction" / "runtime" / "chemu_ner"
SOURCE_URL = "https://raw.githubusercontent.com/chemu-patent-ie/chemu-patent-ie.github.io/master/chemu_sample/chemu_sample.v3.zip"
GUIDELINE_URL = "https://chemu-patent-ie.github.io/resources/Annotation_Guidelines_CLEF2020_ChEMU_task1.pdf"
DOC_IDS = [f"{index:04d}" for index in range(6)]
LABELS = [
    "EXAMPLE_LABEL",
    "REACTION_PRODUCT",
    "STARTING_MATERIAL",
    "REAGENT_CATALYST",
    "SOLVENT",
    "OTHER_COMPOUND",
    "TIME",
    "TEMPERATURE",
    "YIELD_OTHER",
    "YIELD_PERCENT",
]

PROMPT = """Perform ChEMU 2020 Task 1 named-entity extraction on every document in the uploaded JSONL file. Apply the official ChEMU annotation rules below and use the entity's role in context, not merely its chemical name.

First distinguish the reaction stage from work-up, isolation, purification, and analysis. Then identify every explicit occurrence and assign exactly one of these labels:

- `EXAMPLE_LABEL`: only the reaction identifier; exclude words such as "Example", "Step", "Intermediate", or "Reference example", and exclude surrounding brackets, parentheses, colons, and spaces.
- `REACTION_PRODUCT`: every explicit representation of a substance formed by the reaction, including product names, product labels, and representatives such as "title compound".
- `STARTING_MATERIAL`: a consumed substance that provides carbon atoms to an organic product, or any atoms to an inorganic product. Apply this rule even when the substance might commonly be called a reagent.
- `REAGENT_CATALYST`: a compound involved in causing or assisting the reaction, including catalysts, bases, acids, and non-carbon atom donors. Do not use this label for work-up or drying compounds.
- `SOLVENT`: each individual solvent used in the reaction stage. A solvent used only during work-up, extraction, washing, chromatography, or purification is `OTHER_COMPOUND`.
- `OTHER_COMPOUND`: explicit chemical compounds used outside the reaction stage or not belonging to the roles above, including work-up solvents, extraction agents, washing agents, drying agents, and chromatography eluents.
- `TIME`: explicit reaction-duration spans.
- `TEMPERATURE`: explicit temperatures or temperature keywords associated with the procedure. For a stated range, annotate only its lowest and highest temperatures, not intermediate values.
- `YIELD_PERCENT`: only the isolated-yield percentage span.
- `YIELD_OTHER`: only the isolated product amount expressed in mass or amount-of-substance units; keep it separate from `YIELD_PERCENT`.

Boundary rules:

1. Annotate every occurrence separately, because the same chemical may have different roles in reaction and work-up contexts.
2. Use the smallest complete span that expresses the entity. Exclude surrounding quantities, concentrations, punctuation, and descriptive prose unless they are part of the chemical name.
3. Keep separately written product names, product labels, product representatives, yield masses, and yield percentages as separate entities.
4. Extract only explicit spans. Do not infer unmentioned entities or use hidden annotations.
5. Preserve the uploaded text exactly when calculating offsets; do not normalize Unicode, whitespace, or punctuation.

Use a two-pass review before writing the final file:

- Pass 1: identify candidate entities and assign roles after distinguishing reaction from work-up.
- Pass 2: check missed repeated mentions, role consistency, exact boundaries, and label-specific rules.

Write `/mnt/user-data/outputs/predictions.jsonl` with one JSON object per input document:
`{"doc_id":"0000","entities":[{"label":"SOLVENT","start":10,"end":17,"text":"ethanol"}]}`

Offsets must be zero-based with an exclusive end, and every entity must satisfy `document_text[start:end] == text`. Sort entities by `start`, then `end`, then `label`. Use code only to calculate offsets and validate the final output; do not create document-specific hard-coded extraction functions. Also write a concise `/mnt/user-data/outputs/report.md` containing document count, entity count by label, and validation status."""


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_ann(doc_id: str, text: str, ann: str) -> dict:
    entities = []
    for line in ann.splitlines():
        if not line.startswith("T"):
            continue
        identifier, annotation, entity_text = line.split("\t", 2)
        parts = annotation.split()
        label = parts[0]
        if label not in LABELS or ";" in annotation:
            continue
        start, end = map(int, parts[1:3])
        if text[start:end] != entity_text:
            raise ValueError(f"{doc_id}/{identifier}: annotation text does not match source span")
        entities.append(
            {
                "label": label,
                "start": start,
                "end": end,
                "text": entity_text,
            }
        )
    entities.sort(key=lambda item: (item["start"], item["end"], item["label"]))
    return {"doc_id": doc_id, "entities": entities}


def main() -> None:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "GVIM-research-demo"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()

    inputs = []
    gold = []
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for doc_id in DOC_IDS:
            prefix = f"chemu_sample/ner/{doc_id}"
            text = archive.read(f"{prefix}.txt").decode("utf-8")
            ann = archive.read(f"{prefix}.ann").decode("utf-8")
            inputs.append({"doc_id": doc_id, "text": text})
            gold.append(parse_ann(doc_id, text, ann))

    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(DEMO_DIR / "chemu_ner_input.jsonl", inputs)
    write_jsonl(RUNTIME_DIR / "gold" / "chemu_ner_gold.jsonl", gold)
    (DEMO_DIR / "PROMPT.md").write_text(PROMPT, encoding="utf-8", newline="\n")
    manifest = {
        "benchmark": "ChEMU 2020 Task 1 sample v3",
        "task": "chemical synthesis named entity extraction",
        "source_url": SOURCE_URL,
        "annotation_guideline_url": GUIDELINE_URL,
        "input_file": "chemu_ner_input.jsonl",
        "n_documents": len(inputs),
        "n_characters": sum(len(item["text"]) for item in inputs),
        "entity_labels": LABELS,
        "prediction_format": "JSONL with doc_id and entities(label,start,end,text)",
        "official_metrics": [
            "exact-match precision",
            "exact-match recall",
            "exact-match F1",
            "relaxed-match precision",
            "relaxed-match recall",
            "relaxed-match F1",
        ],
    }
    (DEMO_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"Prepared {len(inputs)} ChEMU documents, "
        f"{manifest['n_characters']} characters, "
        f"{sum(len(item['entities']) for item in gold)} gold entities"
    )


if __name__ == "__main__":
    main()
