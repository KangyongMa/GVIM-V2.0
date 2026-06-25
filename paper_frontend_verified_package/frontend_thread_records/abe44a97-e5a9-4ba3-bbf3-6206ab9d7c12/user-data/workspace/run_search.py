#!/usr/bin/env python3
"""MS/MS spectral library search using matchms with normalized cosine similarity."""

import json
import csv
import sys
import os
from collections import defaultdict

# ---------------------------------------------------------------------------
# 1. Paths (using standard GVIM paths)
# ---------------------------------------------------------------------------
UPLOAD_DIR = "E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/4214b5a2-6e1a-42da-9c2a-697cfe80f9de/threads/abe44a97-e5a9-4ba3-bbf3-6206ab9d7c12/user-data/uploads"
OUTPUT_DIR = "E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/4214b5a2-6e1a-42da-9c2a-697cfe80f9de/threads/abe44a97-e5a9-4ba3-bbf3-6206ab9d7c12/user-data/outputs"

QUERY_PATH = os.path.join(UPLOAD_DIR, "query_spectra.mgf")
LIBRARY_PATH = os.path.join(UPLOAD_DIR, "reference_library.mgf")
OUT_CSV = os.path.join(OUTPUT_DIR, "ranked_candidates.csv")
OUT_META = os.path.join(OUTPUT_DIR, "run_metadata.json")
OUT_REPORT = os.path.join(OUTPUT_DIR, "report.md")

# ---------------------------------------------------------------------------
# 2. Load matchms
# ---------------------------------------------------------------------------
from matchms.importing import load_from_mgf
from matchms.similarity import CosineGreedy
from matchms.filtering import normalize_intensities

# ---------------------------------------------------------------------------
# 3. Load spectra
# ---------------------------------------------------------------------------
def load_spectra(path, label):
    spectra = list(load_from_mgf(path))
    print(f"Loaded {len(spectra)} {label} spectra from {path}")
    for sp in spectra:
        sp = normalize_intensities(sp)
        sp.set("label", label)
    return spectra

queries = load_spectra(QUERY_PATH, "query")
library = load_spectra(LIBRARY_PATH, "library")

# ---------------------------------------------------------------------------
# 4. Similarity calculator
# ---------------------------------------------------------------------------
similarity = CosineGreedy(tolerance=0.1)

# ---------------------------------------------------------------------------
# 5. Compare every query against every library spectrum
#    CosineGreedy.pair returns a tuple (score, n_matched) in matchms >= 0.25
#    but in 0.33.x it returns a 2-element array. Unpack robustly.
# ---------------------------------------------------------------------------
all_candidates = []

for qi, query in enumerate(queries):
    q_id = query.metadata.get("title", f"query_{qi+1}")
    q_accession = query.metadata.get("accession", "")
    q_inchikey = query.metadata.get("inchikey", "")

    for ri, ref in enumerate(library):
        result = similarity.pair(query, ref)

        # In matchms 0.33.x, pair returns a numpy 0-d structured array
        # with dtype [('score', '<f8'), ('matches', '<i8')].
        # Use .item() to get the inner tuple reliably.
        if hasattr(result, "item"):
            item = result.item()
            if isinstance(item, tuple):
                cosine_score = float(item[0]) if item[0] is not None else 0.0
                n_matched = int(item[1]) if len(item) > 1 and item[1] is not None else 0
            else:
                cosine_score = float(item) if item is not None else 0.0
                n_matched = 0
        elif hasattr(result, "__iter__") and not isinstance(result, (int, float)):
            items = list(result)
            cosine_score = float(items[0]) if items[0] is not None else 0.0
            n_matched = int(items[1]) if len(items) > 1 and items[1] is not None else 0
        else:
            cosine_score = float(result) if result is not None else 0.0
            n_matched = 0

        r_title = ref.metadata.get("title", f"candidate_{ri+1}")
        r_accession = ref.metadata.get("accession", "")
        r_inchikey = ref.metadata.get("inchikey", "")
        r_name = ref.metadata.get("compound_name", "")

        all_candidates.append({
            "query_id": q_id,
            "query_accession": q_accession,
            "query_inchikey": q_inchikey,
            "candidate_accession": r_accession,
            "candidate_inchikey": r_inchikey,
            "candidate_name": r_name,
            "cosine_score": round(cosine_score, 6),
            "matched_peaks": n_matched,
        })

# ---------------------------------------------------------------------------
# 6. Rank candidates per query by descending cosine score
# ---------------------------------------------------------------------------
ranked_by_query = defaultdict(list)
for cand in all_candidates:
    ranked_by_query[cand["query_id"]].append(cand)

rows = []
for qid in sorted(ranked_by_query.keys()):
    candidates = ranked_by_query[qid]
    candidates.sort(key=lambda x: x["cosine_score"], reverse=True)
    for rank_idx, cand in enumerate(candidates, start=1):
        rows.append({
            "query_id": cand["query_id"],
            "query_accession": cand["query_accession"],
            "query_inchikey": cand["query_inchikey"],
            "candidate_accession": cand["candidate_accession"],
            "candidate_inchikey": cand["candidate_inchikey"],
            "candidate_name": cand["candidate_name"],
            "rank": rank_idx,
            "cosine_score": cand["cosine_score"],
            "matched_peaks": cand["matched_peaks"],
        })

# ---------------------------------------------------------------------------
# 7. Write CSV
# ---------------------------------------------------------------------------
os.makedirs(OUTPUT_DIR, exist_ok=True)

fieldnames = [
    "query_id", "query_accession", "query_inchikey",
    "candidate_accession", "candidate_inchikey",
    "candidate_name", "rank", "cosine_score", "matched_peaks",
]
with open(OUT_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} rows to {OUT_CSV}")

# ---------------------------------------------------------------------------
# 8. Compute summary statistics
# ---------------------------------------------------------------------------
n_queries = len(queries)
n_library = len(library)
n_candidate_pairs = len(all_candidates)

# Per-query: top-k correctness based on InChIKey match
query_inchikeys = {}
for sp in queries:
    qid = sp.metadata.get("title", "")
    ik = sp.metadata.get("inchikey", "")
    query_inchikeys[qid] = ik

top1_correct = 0
top3_correct = 0
top5_correct = 0
reciprocal_ranks = []

for qid in sorted(ranked_by_query.keys()):
    candidates = ranked_by_query[qid]
    q_ik = query_inchikeys.get(qid, "")
    correct_rank = None
    for i, cand in enumerate(candidates):
        if cand["candidate_inchikey"] == q_ik:
            correct_rank = i + 1
            break
    if correct_rank is not None:
        if correct_rank == 1:
            top1_correct += 1
        if correct_rank <= 3:
            top3_correct += 1
        if correct_rank <= 5:
            top5_correct += 1
        reciprocal_ranks.append(1.0 / correct_rank)
    else:
        reciprocal_ranks.append(0.0)

top1_acc = top1_correct / n_queries
top3_acc = top3_correct / n_queries
top5_acc = top5_correct / n_queries
mrr = sum(reciprocal_ranks) / n_queries

# ---------------------------------------------------------------------------
# 9. Write metadata JSON
# ---------------------------------------------------------------------------
metadata = {
    "benchmark": "MassBank MS/MS candidate retrieval mini-benchmark",
    "algorithm": "matchms CosineGreedy (normalized cosine similarity)",
    "fragment_mz_tolerance": 0.1,
    "n_queries": n_queries,
    "n_library_spectra": n_library,
    "n_candidate_pairs": n_candidate_pairs,
    "top1_accuracy": top1_acc,
    "top3_accuracy": top3_acc,
    "top5_accuracy": top5_acc,
    "MRR": round(mrr, 6),
}

with open(OUT_META, "w") as f:
    json.dump(metadata, f, indent=2)
print(f"Wrote metadata to {OUT_META}")

# ---------------------------------------------------------------------------
# 10. Write report Markdown
# ---------------------------------------------------------------------------
report_md = f"""# MS/MS Spectral Library Search Report

## Data

- **Query file**: `query_spectra.mgf` — {n_queries} spectra
- **Reference library**: `reference_library.mgf` — {n_library} spectra

## Algorithm

- **Library**: `matchms` with `CosineGreedy` similarity
- **Preprocessing**: `normalize_intensities` applied to all spectra
- **Similarity metric**: Normalized peak cosine similarity
- **Fragment m/z tolerance**: 0.1 Da

## Results

| Metric | Value |
|--------|-------|
| Number of queries | {n_queries} |
| Library size | {n_library} |
| Candidate pairs evaluated | {n_candidate_pairs} |
| Top-1 accuracy | {top1_acc:.4f} |
| Top-3 accuracy | {top3_acc:.4f} |
| Top-5 accuracy | {top5_acc:.4f} |
| MRR (Mean Reciprocal Rank) | {mrr:.4f} |

## Per-Query Detailed Ranking

| Query | Rank | Candidate | Score | Matched Peaks | Correct? |
|-------|------|-----------|-------|---------------|----------|
"""

# Add per-query details with correctness markers
for row in rows:
    q_ik = row["query_inchikey"]
    c_ik = row["candidate_inchikey"]
    is_correct = "✓" if q_ik and c_ik and q_ik == c_ik else ("✗" if q_ik and c_ik else "—")
    report_md += f"| {row['query_id']} | {row['rank']} | {row['candidate_name'] or row['candidate_accession']} | {row['cosine_score']} | {row['matched_peaks']} | {is_correct} |\n"

report_md += f"""
## Output Files

| File | Path |
|------|------|
| Ranked candidates | `{OUT_CSV}` |
| Run metadata | `{OUT_META}` |
| This report | `{OUT_REPORT}` |
"""

with open(OUT_REPORT, "w") as f:
    f.write(report_md)
print(f"Wrote report to {OUT_REPORT}")
print("Done.")
