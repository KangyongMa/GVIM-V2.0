#!/usr/bin/env python
"""Stage 2: Full temporal external validation analysis for BACE1 project."""

import pandas as pd
import numpy as np
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score

# Load and merge data
pred = pd.read_csv('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/external_predictions.csv')
gold = pd.read_csv('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/uploads/bace1_late_external_gold.csv')
df = pred.merge(gold, on='compound_id', how='inner')
assert len(df) == 1598, f"Expected 1598 rows, got {len(df)}"

print(f"=== Data merged: {len(df)} rows ===")
print(f"scaffold_novel distribution:\n{df['scaffold_novel'].value_counts()}")
print(f"pIC50 range: {df['pIC50'].min():.3f} - {df['pIC50'].max():.3f}")

# Regression metrics
def reg_metrics(y_true, y_pred, label):
    errs = y_pred - y_true
    mae = float(np.mean(np.abs(errs)))
    rmse = float(np.sqrt(np.mean(errs**2)))
    r2 = float(r2_score(y_true, y_pred))
    pearson = float(np.corrcoef(y_true, y_pred)[0, 1])
    return {'model': label, 'MAE': round(mae, 4), 'RMSE': round(rmse, 4), 'R2': round(r2, 4), 'Pearson_r': round(pearson, 4)}

reg = [
    reg_metrics(df['pIC50'], df['prediction_selected'], 'RandomForest'),
    reg_metrics(df['pIC50'], df['prediction_ridge'], 'Ridge'),
    reg_metrics(df['pIC50'], df['prediction_mean'], 'Mean Baseline'),
]
print("\n=== Regression Metrics ===")
for r in reg:
    print(f"  {r['model']}: MAE={r['MAE']}, RMSE={r['RMSE']}, R2={r['R2']}, r={r['Pearson_r']}")

# Ranking metrics
def rank_metrics(subset, label):
    n = len(subset)
    k = max(1, int(np.ceil(n * 0.10)))
    active_thresh = subset['pIC50'].quantile(0.9)
    active_mask = subset['pIC50'] >= active_thresh
    n_actives = int(active_mask.sum())
    df_s = subset.sort_values(['prediction_selected', 'compound_id'], ascending=[False, True])
    selected_ids = df_s.head(k)['compound_id']
    selected_mask = subset['compound_id'].isin(selected_ids)
    hits = int((active_mask & selected_mask).sum())
    recall = float(hits / n_actives) if n_actives else 0.0
    frac_act_sel = hits / k if k else 0
    frac_act_all = n_actives / n if n else 0
    ef = float(frac_act_sel / frac_act_all) if frac_act_all else 0.0
    return {'subset': label, 'n': n, 'k': k, 'n_actives': n_actives,
            'active_threshold': round(float(active_thresh), 4),
            'hits_in_top_k': hits,
            'recall_at_k': round(recall, 4),
            'enrichment_factor': round(ef, 4)}

rank_all = rank_metrics(df, 'all_external')
rank_novel = rank_metrics(df[df['scaffold_novel'] == 1], 'scaffold_novel_1')
rank_known = rank_metrics(df[df['scaffold_novel'] == 0], 'scaffold_novel_0')

print("\n=== Ranking Metrics ===")
for rk in [rank_all, rank_known, rank_novel]:
    print(f"  {rk['subset']}: recall={rk['recall_at_k']}, EF={rk['enrichment_factor']}, hits={rk['hits_in_top_k']}/{rk['n_actives']}")

# Save metrics.json
metrics_out = {
    'regression_metrics': reg,
    'ranking_metrics': [rank_all, rank_known, rank_novel],
    'n_external': 1598,
    'n_scaffold_novel': int(df['scaffold_novel'].sum())
}
with open('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/metrics.json', 'w') as f:
    json.dump(metrics_out, f, indent=2)
print("\nSaved metrics.json")

# Save external_predictions_with_gold.csv
df.to_csv('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/external_predictions_with_gold.csv', index=False)
print("Saved external_predictions_with_gold.csv")

# Save top_candidates.csv
df_sorted = df.sort_values(['prediction_selected', 'compound_id'], ascending=[False, True])
top160 = df_sorted.head(160)
tc = top160[['compound_id', 'prediction_selected', 'prediction_ridge', 'pIC50', 'scaffold_novel']].copy()
tc.columns = ['compound_id', 'prediction_selected', 'prediction_ridge', 'gold_pIC50', 'scaffold_novel']
tc['prediction_error'] = (tc['prediction_selected'] - tc['gold_pIC50']).round(4)
tc.to_csv('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/top_candidates.csv', index=False)
print("Saved top_candidates.csv")

# structure_activity_summary.csv
df['abs_error'] = np.abs(df['prediction_selected'] - df['pIC50'])
df['error_bin'] = pd.cut(df['abs_error'], bins=[0, 0.5, 1.0, 2.0, 100],
                         labels=['<0.5', '0.5-1.0', '1.0-2.0', '>2.0'])
sa_summary = df.groupby(['scaffold_novel', 'error_bin']).agg(
    count=('compound_id', 'count'),
    mean_true=('pIC50', 'mean'),
    mean_pred=('prediction_selected', 'mean')
).reset_index()
sa_summary.to_csv('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/structure_activity_summary.csv', index=False)
print("Saved structure_activity_summary.csv")

# FIGURE 1: Temporal Validation
plt.rcParams.update({'font.size': 12})
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

colors = df['scaffold_novel'].map({0: '#2196F3', 1: '#FF5722'})
ax = axes[0]
ax.scatter(df['pIC50'], df['prediction_selected'], c=colors, alpha=0.4, s=12, edgecolors='none')
lims = [2, 12]
ax.plot(lims, lims, 'k--', alpha=0.3, lw=1)
ax.set_xlim(lims); ax.set_ylim(lims)
ax.set_xlabel('Experimental pIC50', fontsize=13)
ax.set_ylabel('Predicted pIC50 (Random Forest)', fontsize=13)
ax.set_title('Temporal External Validation', fontsize=14, fontweight='bold')
rf_met = reg[0]
ax.text(2.5, 11.2, f'MAE={rf_met["MAE"]:.3f}  RMSE={rf_met["RMSE"]:.3f}\nR2={rf_met["R2"]:.3f}  r={rf_met["Pearson_r"]:.3f}',
        fontsize=11, bbox=dict(boxstyle='round,pad=0.4', facecolor='wheat', alpha=0.6))
ax.legend([plt.Line2D([0],[0],marker='o',color='w',markerfacecolor='#2196F3',markersize=8),
           plt.Line2D([0],[0],marker='o',color='w',markerfacecolor='#FF5722',markersize=8)],
          ['Known scaffold (n=323)', 'Novel scaffold (n=1275)'], loc='lower right', fontsize=10)
ax.grid(True, alpha=0.3)

residuals = df['prediction_selected'] - df['pIC50']
ax = axes[1]
ax.hist(residuals, bins=50, color='#4CAF50', alpha=0.7, edgecolor='white', linewidth=0.3)
ax.axvline(0, color='red', linestyle='--', alpha=0.6, lw=1.5)
ax.set_xlabel('Residual (Predicted - Experimental)', fontsize=13)
ax.set_ylabel('Count', fontsize=13)
ax.set_title('Prediction Error Distribution', fontsize=14, fontweight='bold')
ax.text(0.95, 0.95, f'Mean={np.mean(residuals):.3f}\nStd={np.std(residuals):.3f}',
        transform=ax.transAxes, fontsize=11, va='top', ha='right',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='wheat', alpha=0.6))
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/figure_temporal_validation.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved figure_temporal_validation.png")

# FIGURE 2: Scaffold Generalization
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

known = df[df['scaffold_novel'] == 0]
novel = df[df['scaffold_novel'] == 1]
def gmet(subset):
    errs = subset['prediction_selected'] - subset['pIC50']
    return {'MAE': float(np.mean(np.abs(errs))), 'RMSE': float(np.sqrt(np.mean(errs**2))), 'n': len(subset)}
km = gmet(known); nm = gmet(novel)

ax = axes[0]
x = np.arange(2); w = 0.35
ax.bar(x[0], km['MAE'], w, label='Known scaffold', color='#2196F3', alpha=0.85, edgecolor='white')
ax.bar(x[0]+w, nm['MAE'], w, label='Novel scaffold', color='#FF5722', alpha=0.85, edgecolor='white')
ax.bar(x[1], km['RMSE'], w, label='_', color='#1565C0', alpha=0.85, edgecolor='white')
ax.bar(x[1]+w, nm['RMSE'], w, label='_', color='#BF360C', alpha=0.85, edgecolor='white')
ax.set_xticks(x + w/2)
ax.set_xticklabels(['MAE', 'RMSE'], fontsize=12)
ax.set_ylabel('Error (pIC50 units)', fontsize=12)
ax.set_title('Prediction Error by Scaffold Type', fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3, axis='y')
for bar in ax.patches:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, h + 0.02, f'{h:.3f}', ha='center', fontsize=9)

ax = axes[1]
labels_plot = ['All\nexternal', 'Known\nscaffold', 'Novel\nscaffold']
recall_vals = [rank_all['recall_at_k'], rank_known['recall_at_k'], rank_novel['recall_at_k']]
ef_vals = [rank_all['enrichment_factor'], rank_known['enrichment_factor'], rank_novel['enrichment_factor']]
colors_bar = ['#4CAF50', '#2196F3', '#FF5722']
ax.bar(range(3), recall_vals, 0.5, color=colors_bar, alpha=0.85, edgecolor='white')
ax.set_xticks(range(3))
ax.set_xticklabels(labels_plot, fontsize=11)
ax.set_ylabel('Top-10% Recall', fontsize=12)
ax.set_ylim(0, 1.05)
ax.set_title('Virtual Screening: Top-10% Recall at Budget=10%', fontsize=14, fontweight='bold')
for i, (rv, ef) in enumerate(zip(recall_vals, ef_vals)):
    ax.text(i, rv + 0.02, f'Rec={rv:.3f}\nEF={ef:.2f}', ha='center', fontsize=10, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/figure_scaffold_generalization.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved figure_scaffold_generalization.png")

# Sanity check
with open('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/uploads/task_manifest.json') as f:
    tm = json.load(f)
with open('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/uploads/dataset_summary.json') as f:
    ds = json.load(f)
print(f"\n=== Task Manifest ===")
print(json.dumps(tm, indent=2))
print(f"\n=== Dataset Summary ===")
print(json.dumps(ds, indent=2))

print("\n=== DONE ===")
import os
for f in ['E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/metrics.json',
          'E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/external_predictions_with_gold.csv',
          'E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/top_candidates.csv',
          'E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/structure_activity_summary.csv',
          'E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/figure_temporal_validation.png',
          'E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs/figure_scaffold_generalization.png']:
    if os.path.exists(f):
        print(f"  OK {f}")
