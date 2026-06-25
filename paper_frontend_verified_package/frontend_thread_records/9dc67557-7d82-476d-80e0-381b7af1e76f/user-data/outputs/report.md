# Reaction Data Extraction Report

**Source:** nanomaterials-12-01070.pdf (Table 2, Page 6)
**Extraction tool:** reaction-data-extraction skill (MinerU API + rule-based parsing)
**Date:** 2026-06-15

## Table 2 — Optimization of the Reaction Conditions

| Entry | Catalyst | Solvent (v/v) | T (°C) | Yield (%) |
|-------|----------|---------------|--------|-----------|
| 1 | Cu(im)_2 | H_2O | 50 | 20 |
| 2 | - | H_2O | 50 | trace |
| 3 | Cu@N-C(400) | H_2O | 50 | 83 |
| 4 | Cu@N-C(600) | H_2O | 50 | 94 |
| 5 | Cu@N-C(800) | H_2O | 50 | 78 |
| 6 | Cu@N-C(600) | EtOH | 50 | 90 |
| 7 | Cu@N-C(600) | i-PrOH | 50 | 68 |
| 8 | Cu@N-C(600) | t-BuOH | 50 | 7 |
| 9 | Cu@N-C(600) | EtOH/ H_2O  (3/1) | 50 | 96 |
| 10 | Cu@N-C(600) | EtOH/ H_2O  (1/3) | 50 | 88 |
| 11 | Cu@N-C(600) | EtOH/ H_2O  (1/1) | 50 | 40 |
| 12 | Cu@N-C(600) | i-PrOH/ H_2O  (3/1) | 50 | 92 |
| 13 | Cu@N-C(600) | i-PrOH/ H_2O  (1/3) | 50 | 86 |
| 14 | Cu@N-C(600) | i-PrOH/ H_2O  (1/1) | 50 | 74 |
| 15 | Cu@N-C(600) | t-BuOH/ H_2O  (3/1) | 50 | 98 |
| 16 | Cu@N-C(600) | t-BuOH/ H_2O  (1/3) | 50 | 45 |
| 17 | Cu@N-C(600) | t-BuOH/ H_2O  (1/1) | 50 | 55 |
| 18 | Cu@N-C(600) | t-BuOH/ H_2O  (3/1) | 50 | 80 |
| 19 | Cu@N-C(600) | t-BuOH/ H_2O  (3/1) | 40 | 56 |
| 20 | Cu@N-C(600) | t-BuOH/ H_2O  (3/1) | 25 | 50 |
| 21 | CuSO_4 + NaAsc | t-BuOH/ H_2O  (3/1) | 50 | 88 |

## Summary

- **Total entries extracted:** 21
- **Catalysts tested:** Cu(im)₂, Cu@N-C(400), Cu@N-C(600), Cu@N-C(800), CuSO₄ + NaAsc
- **Solvents:** H₂O, EtOH, i-PrOH, t-BuOH, and binary mixtures with H₂O
- **Temperature range:** 25–50 °C
- **Best result:** Entry 15 — Cu@N-C(600), t-BuOH/H₂O (3/1), 50 °C, 98% yield

## Notes

- Entry 2: No catalyst (control experiment) — trace yield
- Entry 18: Same as entry 15 but with 5 mg catalyst instead of 10 mg — 80% yield
- Entry 21: Homogeneous CuSO₄ + NaAsc system — 88% yield