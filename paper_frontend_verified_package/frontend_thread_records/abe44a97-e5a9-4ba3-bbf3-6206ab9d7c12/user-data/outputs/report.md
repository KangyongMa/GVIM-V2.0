# MS/MS Spectral Library Search Report

## Data

- **Query file**: `query_spectra.mgf` — 5 spectra
- **Reference library**: `reference_library.mgf` — 15 spectra

## Algorithm

- **Library**: `matchms` with `CosineGreedy` similarity
- **Preprocessing**: `normalize_intensities` applied to all spectra
- **Similarity metric**: Normalized peak cosine similarity
- **Fragment m/z tolerance**: 0.1 Da

## Results

| Metric | Value |
|--------|-------|
| Number of queries | 5 |
| Library size | 15 |
| Candidate pairs evaluated | 75 |
| Top-1 accuracy | 0.8000 |
| Top-3 accuracy | 1.0000 |
| Top-5 accuracy | 1.0000 |
| MRR (Mean Reciprocal Rank) | 0.9000 |

## Per-Query Detailed Ranking

| Query | Rank | Candidate | Score | Matched Peaks | Correct? |
|-------|------|-----------|-------|---------------|----------|
| query_1 | 1 | Nocuolin A | 0.886387 | 12 | ✓ |
| query_1 | 2 | Nocuolin A | 0.523804 | 11 | ✓ |
| query_1 | 3 | Nocuolin A | 0.290321 | 10 | ✓ |
| query_1 | 4 | Nocuolin A | 0.263529 | 9 | ✓ |
| query_1 | 5 | Nocuolin A | 0.222953 | 7 | ✓ |
| query_1 | 6 | Nocuolin A | 0.187156 | 5 | ✓ |
| query_1 | 7 | Nocuolin A | 0.145512 | 4 | ✓ |
| query_1 | 8 | Nocuolin A | 0.117273 | 3 | ✓ |
| query_1 | 9 | Nocuolin A | 0.021544 | 1 | ✓ |
| query_1 | 10 | Nocuolin A | 0.020222 | 1 | ✓ |
| query_1 | 11 | Nocuolin A | 0.015956 | 1 | ✓ |
| query_1 | 12 | Pseudospumigin A | 0.013693 | 1 | ✗ |
| query_1 | 13 | Portoamide A | 0.0 | 0 | ✗ |
| query_1 | 14 | Portoamide B | 0.0 | 0 | ✗ |
| query_1 | 15 | Namalide D | 0.0 | 0 | ✗ |
| query_2 | 1 | Portoamide B | 0.993599 | 6 | ✗ |
| query_2 | 2 | Portoamide A | 0.940263 | 4 | ✓ |
| query_2 | 3 | Nocuolin A | 0.00285 | 1 | ✗ |
| query_2 | 4 | Nocuolin A | 0.002633 | 1 | ✗ |
| query_2 | 5 | Nocuolin A | 0.002289 | 1 | ✗ |
| query_2 | 6 | Nocuolin A | 0.0 | 0 | ✗ |
| query_2 | 7 | Namalide D | 0.0 | 0 | ✗ |
| query_2 | 8 | Pseudospumigin A | 0.0 | 0 | ✗ |
| query_2 | 9 | Nocuolin A | 0.0 | 0 | ✗ |
| query_2 | 10 | Nocuolin A | 0.0 | 0 | ✗ |
| query_2 | 11 | Nocuolin A | 0.0 | 0 | ✗ |
| query_2 | 12 | Nocuolin A | 0.0 | 0 | ✗ |
| query_2 | 13 | Nocuolin A | 0.0 | 0 | ✗ |
| query_2 | 14 | Nocuolin A | 0.0 | 0 | ✗ |
| query_2 | 15 | Nocuolin A | 0.0 | 0 | ✗ |
| query_3 | 1 | Portoamide B | 0.849837 | 4 | ✓ |
| query_3 | 2 | Portoamide A | 0.717889 | 3 | ✗ |
| query_3 | 3 | Nocuolin A | 0.0 | 0 | ✗ |
| query_3 | 4 | Namalide D | 0.0 | 0 | ✗ |
| query_3 | 5 | Pseudospumigin A | 0.0 | 0 | ✗ |
| query_3 | 6 | Nocuolin A | 0.0 | 0 | ✗ |
| query_3 | 7 | Nocuolin A | 0.0 | 0 | ✗ |
| query_3 | 8 | Nocuolin A | 0.0 | 0 | ✗ |
| query_3 | 9 | Nocuolin A | 0.0 | 0 | ✗ |
| query_3 | 10 | Nocuolin A | 0.0 | 0 | ✗ |
| query_3 | 11 | Nocuolin A | 0.0 | 0 | ✗ |
| query_3 | 12 | Nocuolin A | 0.0 | 0 | ✗ |
| query_3 | 13 | Nocuolin A | 0.0 | 0 | ✗ |
| query_3 | 14 | Nocuolin A | 0.0 | 0 | ✗ |
| query_3 | 15 | Nocuolin A | 0.0 | 0 | ✗ |
| query_4 | 1 | Namalide D | 0.697163 | 9 | ✓ |
| query_4 | 2 | Nocuolin A | 0.0 | 0 | ✗ |
| query_4 | 3 | Portoamide A | 0.0 | 0 | ✗ |
| query_4 | 4 | Portoamide B | 0.0 | 0 | ✗ |
| query_4 | 5 | Pseudospumigin A | 0.0 | 0 | ✗ |
| query_4 | 6 | Nocuolin A | 0.0 | 0 | ✗ |
| query_4 | 7 | Nocuolin A | 0.0 | 0 | ✗ |
| query_4 | 8 | Nocuolin A | 0.0 | 0 | ✗ |
| query_4 | 9 | Nocuolin A | 0.0 | 0 | ✗ |
| query_4 | 10 | Nocuolin A | 0.0 | 0 | ✗ |
| query_4 | 11 | Nocuolin A | 0.0 | 0 | ✗ |
| query_4 | 12 | Nocuolin A | 0.0 | 0 | ✗ |
| query_4 | 13 | Nocuolin A | 0.0 | 0 | ✗ |
| query_4 | 14 | Nocuolin A | 0.0 | 0 | ✗ |
| query_4 | 15 | Nocuolin A | 0.0 | 0 | ✗ |
| query_5 | 1 | Pseudospumigin A | 0.914877 | 5 | ✓ |
| query_5 | 2 | Nocuolin A | 0.347232 | 1 | ✗ |
| query_5 | 3 | Nocuolin A | 0.325921 | 1 | ✗ |
| query_5 | 4 | Nocuolin A | 0.257168 | 1 | ✗ |
| query_5 | 5 | Nocuolin A | 0.03698 | 1 | ✗ |
| query_5 | 6 | Nocuolin A | 0.036198 | 1 | ✗ |
| query_5 | 7 | Portoamide A | 0.0 | 0 | ✗ |
| query_5 | 8 | Portoamide B | 0.0 | 0 | ✗ |
| query_5 | 9 | Namalide D | 0.0 | 0 | ✗ |
| query_5 | 10 | Nocuolin A | 0.0 | 0 | ✗ |
| query_5 | 11 | Nocuolin A | 0.0 | 0 | ✗ |
| query_5 | 12 | Nocuolin A | 0.0 | 0 | ✗ |
| query_5 | 13 | Nocuolin A | 0.0 | 0 | ✗ |
| query_5 | 14 | Nocuolin A | 0.0 | 0 | ✗ |
| query_5 | 15 | Nocuolin A | 0.0 | 0 | ✗ |

## Output Files

| File | Path |
|------|------|
| Ranked candidates | `E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/4214b5a2-6e1a-42da-9c2a-697cfe80f9de/threads/abe44a97-e5a9-4ba3-bbf3-6206ab9d7c12/user-data/outputs\ranked_candidates.csv` |
| Run metadata | `E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/4214b5a2-6e1a-42da-9c2a-697cfe80f9de/threads/abe44a97-e5a9-4ba3-bbf3-6206ab9d7c12/user-data/outputs\run_metadata.json` |
| This report | `E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/4214b5a2-6e1a-42da-9c2a-697cfe80f9de/threads/abe44a97-e5a9-4ba3-bbf3-6206ab9d7c12/user-data/outputs\report.md` |
