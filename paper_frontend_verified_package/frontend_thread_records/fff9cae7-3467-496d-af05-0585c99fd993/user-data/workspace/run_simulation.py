import pandas as pd
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.preprocessing import StandardScaler
import json, csv, os, warnings
warnings.filterwarnings('ignore')

# =====================================================================
# 1. Load and prepare data
# =====================================================================
df = pd.read_csv('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/0d253518-3b38-4d96-aba9-4675f48f3fca/threads/fff9cae7-3467-496d-af05-0585c99fd993/user-data/uploads/bace_active_discovery.csv')
print(f"Loaded {len(df)} molecules")

exclude_cols = {'row_id', 'mol', 'CID', 'Class', 'Model', 'pIC50', 'canvasUID'}
descriptor_cols = [c for c in df.columns if c not in exclude_cols]
print(f"Using {len(descriptor_cols)} molecular descriptor features")

X_all = df[descriptor_cols].values.astype(np.float64)
y_all = df['pIC50'].values.astype(np.float64)
n_mol = len(df)

threshold = np.percentile(y_all, 95)
high_activity_indices = np.where(y_all >= threshold)[0]
n_high = len(high_activity_indices)
print(f"High-activity threshold: pIC50 >= {threshold:.4f}")
print(f"Number of high-activity molecules: {n_high}")

# =====================================================================
# 2. Simulation parameters
# =====================================================================
seeds = list(range(20))
initial_q = 30
batch_size = 10
budget = 150
policies = ['random', 'surrogate_active_search', 'greedy_surrogate', 'ucb_surrogate']
n_batches = (budget - initial_q) // batch_size

# =====================================================================
# 3. Simulation loop
# =====================================================================
results = {}
trajectories_list = []
source_data_list = []

for policy_name in policies:
    print(f"\n{'='*60}")
    print(f"Running policy: {policy_name}")
    print('='*60)
    
    per_seed_metrics = {}
    
    for seed in seeds:
        rng = np.random.RandomState(seed)
        idx_pool = np.arange(n_mol)
        rng.shuffle(idx_pool)
        queried = idx_pool[:initial_q].tolist()
        unqueried = idx_pool[initial_q:].tolist()
        
        cumulative_hits = [sum(1 for i in queried if i in high_activity_indices)]
        best_pIC50_sofar = [float(np.max(y_all[queried]))]
        
        if policy_name == 'random':
            rng.shuffle(unqueried)
            for batch_idx in range(n_batches):
                batch = unqueried[:batch_size]
                queried.extend(batch)
                unqueried = unqueried[batch_size:]
                cumulative_hits.append(sum(1 for i in queried if i in high_activity_indices))
                best_pIC50_sofar.append(float(np.max(y_all[queried])))
        else:
            for batch_idx in range(n_batches):
                X_queried = X_all[queried]
                y_queried = y_all[queried]
                scaler = StandardScaler()
                X_queried_scaled = scaler.fit_transform(X_queried)
                
                model = ExtraTreesRegressor(
                    n_estimators=200, max_depth=15, 
                    min_samples_leaf=3, random_state=seed,
                    n_jobs=-1
                )
                model.fit(X_queried_scaled, y_queried)
                
                if len(unqueried) == 0:
                    break
                X_unqueried = X_all[unqueried]
                X_unqueried_scaled = scaler.transform(X_unqueried)
                preds = model.predict(X_unqueried_scaled)
                
                if policy_name == 'ucb_surrogate':
                    tree_preds = np.array([
                        tree.predict(X_unqueried_scaled) 
                        for tree in model.estimators_
                    ])
                    uncertainties = tree_preds.std(axis=0)
                    scores = preds + 1.0 * uncertainties
                else:
                    scores = preds
                
                top_indices_in_unqueried = np.argsort(scores)[::-1][:batch_size]
                batch = [unqueried[i] for i in top_indices_in_unqueried]
                
                queried.extend(batch)
                unqueried = [unqueried[i] for i in range(len(unqueried)) if i not in top_indices_in_unqueried]
                
                cumulative_hits.append(sum(1 for i in queried if i in high_activity_indices))
                best_pIC50_sofar.append(float(np.max(y_all[queried])))
        
        recall = cumulative_hits[-1] / n_high
        hit_rate = cumulative_hits[-1] / budget
        ef = cumulative_hits[-1] / (budget * n_high / n_mol) if n_high > 0 else 0
        best_pIC50 = best_pIC50_sofar[-1]
        
        per_seed_metrics[seed] = {
            'recall_at_150': recall,
            'hit_rate_at_150': hit_rate,
            'enrichment_factor_at_150': ef,
            'best_pIC50_at_150': best_pIC50,
            'cumulative_hits': cumulative_hits,
            'best_pIC50_traj': best_pIC50_sofar
        }
        
        for step, (hits, best) in enumerate(zip(cumulative_hits, best_pIC50_sofar)):
            n_queried = initial_q + step * batch_size
            trajectories_list.append({
                'policy': policy_name,
                'seed': seed,
                'n_queried': n_queried,
                'cumulative_high_activity_found': hits,
                'recall': hits / n_high,
                'best_pIC50_sofar': best
            })
        
        source_data_list.append({
            'policy': policy_name,
            'seed': seed,
            'recall_at_150': recall,
            'hit_rate_at_150': hit_rate,
            'enrichment_factor_at_150': ef,
            'best_pIC50_at_150': best_pIC50
        })
        
        print(f"  Seed {seed:2d}: Recall={recall:.4f}, HitRate={hit_rate:.4f}, EF={ef:.2f}, Best={best_pIC50:.4f}")
    
    results[policy_name] = per_seed_metrics

# =====================================================================
# 4. Bootstrap CI for active-search minus random Recall@150
# =====================================================================
n_bootstrap = 10000
np.random.seed(42)
diffs = np.array([results['surrogate_active_search'][s]['recall_at_150'] 
                   - results['random'][s]['recall_at_150'] for s in seeds])
bootstrap_diffs = np.random.choice(diffs, size=(n_bootstrap, len(seeds)), replace=True).mean(axis=1)
ci_lower, ci_upper = np.percentile(bootstrap_diffs, [2.5, 97.5])
print(f"\nBootstrap 95% CI for active-search minus random Recall@150: [{ci_lower:.4f}, {ci_upper:.4f}]")

for pol in ['greedy_surrogate', 'ucb_surrogate']:
    diffs_p = np.array([results[pol][s]['recall_at_150'] 
                        - results['random'][s]['recall_at_150'] for s in seeds])
    bootstrap_diffs_p = np.random.choice(diffs_p, size=(n_bootstrap, len(seeds)), replace=True).mean(axis=1)
    ci_l_p, ci_u_p = np.percentile(bootstrap_diffs_p, [2.5, 97.5])
    print(f"Bootstrap 95% CI for {pol} minus random Recall@150: [{ci_l_p:.4f}, {ci_u_p:.4f}]")

# =====================================================================
# 5. Aggregate metrics
# =====================================================================
aggregated = {}
for policy_name in policies:
    recalls = [results[policy_name][s]['recall_at_150'] for s in seeds]
    hit_rates = [results[policy_name][s]['hit_rate_at_150'] for s in seeds]
    efs = [results[policy_name][s]['enrichment_factor_at_150'] for s in seeds]
    bests = [results[policy_name][s]['best_pIC50_at_150'] for s in seeds]
    
    aggregated[policy_name] = {
        'recall_at_150': {
            'mean': float(np.mean(recalls)),
            'std': float(np.std(recalls)),
            'values': [float(v) for v in recalls]
        },
        'hit_rate_at_150': {
            'mean': float(np.mean(hit_rates)),
            'std': float(np.std(hit_rates)),
            'values': [float(v) for v in hit_rates]
        },
        'enrichment_factor_at_150': {
            'mean': float(np.mean(efs)),
            'std': float(np.std(efs)),
            'values': [float(v) for v in efs]
        },
        'best_pIC50_at_150': {
            'mean': float(np.mean(bests)),
            'std': float(np.std(bests)),
            'values': [float(v) for v in bests]
        }
    }

metrics = {
    'experiment_parameters': {
        'dataset': 'bace_active_discovery.csv',
        'n_molecules': n_mol,
        'high_activity_threshold_pIC50': float(threshold),
        'n_high_activity': int(n_high),
        'initial_random_queries': initial_q,
        'batch_size': batch_size,
        'total_budget': budget,
        'n_seeds': len(seeds),
        'policies': policies,
        'surrogate_model': 'ExtraTreesRegressor(n_estimators=200, max_depth=15)',
        'evaluation_note': 'Retrospective virtual screening; pIC50 used as oracle only for querying and final metrics.'
    },
    'aggregated_metrics': aggregated,
    'bootstrap_95_ci_active_minus_random_recall': {
        'lower': float(ci_lower),
        'upper': float(ci_upper),
        'method': '10,000 bootstrap resamples of paired per-seed differences'
    }
}

for pol in ['greedy_surrogate', 'ucb_surrogate']:
    diffs_p = np.array([results[pol][s]['recall_at_150'] - results['random'][s]['recall_at_150'] for s in seeds])
    bd_p = np.random.choice(diffs_p, size=(n_bootstrap, len(seeds)), replace=True).mean(axis=1)
    metrics[f'bootstrap_95_ci_{pol}_minus_random_recall'] = {
        'lower': float(np.percentile(bd_p, 2.5)),
        'upper': float(np.percentile(bd_p, 97.5))
    }

with open('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/0d253518-3b38-4d96-aba9-4675f48f3fca/threads/fff9cae7-3467-496d-af05-0585c99fd993/user-data/outputs/metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)
print("\nSaved metrics.json")

# =====================================================================
# 6. Save trajectories.csv
# =====================================================================
traj_df = pd.DataFrame(trajectories_list)
traj_df.to_csv('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/0d253518-3b38-4d96-aba9-4675f48f3fca/threads/fff9cae7-3467-496d-af05-0585c99fd993/user-data/outputs/trajectories.csv', index=False)
print(f"Saved trajectories.csv ({len(traj_df)} rows)")

# =====================================================================
# 7. Save source_data_budget_metrics.csv
# =====================================================================
src_df = pd.DataFrame(source_data_list)
src_df.to_csv('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/0d253518-3b38-4d96-aba9-4675f48f3fca/threads/fff9cae7-3467-496d-af05-0585c99fd993/user-data/outputs/source_data_budget_metrics.csv', index=False)
print(f"Saved source_data_budget_metrics.csv ({len(src_df)} rows)")

# =====================================================================
# 8. Save final_selected_candidates.csv (surrogate_active_search, seed=19)
# =====================================================================
rng = np.random.RandomState(19)
idx_pool = np.arange(n_mol)
rng.shuffle(idx_pool)
queried = idx_pool[:initial_q].tolist()
unqueried = idx_pool[initial_q:].tolist()

for batch_idx in range(n_batches):
    X_q = X_all[queried]
    y_q = y_all[queried]
    scaler = StandardScaler()
    X_q_scaled = scaler.fit_transform(X_q)
    model = ExtraTreesRegressor(n_estimators=200, max_depth=15, min_samples_leaf=3, random_state=19, n_jobs=-1)
    model.fit(X_q_scaled, y_q)
    X_u = X_all[unqueried]
    X_u_scaled = scaler.transform(X_u)
    preds = model.predict(X_u_scaled)
    top_idx = np.argsort(preds)[::-1][:batch_size]
    batch = [unqueried[i] for i in top_idx]
    queried.extend(batch)
    unqueried = [unqueried[i] for i in range(len(unqueried)) if i not in top_idx]

final_df = df.iloc[queried][['row_id', 'mol', 'CID', 'pIC50']].copy()
final_df['is_high_activity'] = (final_df['pIC50'] >= threshold).astype(int)
final_df['query_order'] = range(1, len(final_df) + 1)
final_df.to_csv('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/0d253518-3b38-4d96-aba9-4675f48f3fca/threads/fff9cae7-3467-496d-af05-0585c99fd993/user-data/outputs/final_selected_candidates.csv', index=False)
print(f"Saved final_selected_candidates.csv ({len(final_df)} molecules)")

# =====================================================================
# 9. Generate recall curve plot
# =====================================================================
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

policy_styles = {
    'random': ('Random', '#888888', '--'),
    'surrogate_active_search': ('Active Search (ET)', '#2166AC', '-'),
    'greedy_surrogate': ('Greedy ET', '#D6604D', '--'),
    'ucb_surrogate': ('UCB ET', '#4DAF4A', ':')
}

fig, ax = plt.subplots(1, 1, figsize=(9, 6))

main_policies = ['random', 'surrogate_active_search']
extra_policies = ['greedy_surrogate', 'ucb_surrogate']

for pol in main_policies + extra_policies:
    label, color, ls = policy_styles[pol]
    pol_traj = traj_df[traj_df['policy'] == pol]
    budget_points = sorted(pol_traj['n_queried'].unique())
    mean_recall = []
    std_recall = []
    for bp in budget_points:
        recalls_at_bp = pol_traj[pol_traj['n_queried'] == bp]['recall'].values
        mean_recall.append(np.mean(recalls_at_bp))
        std_recall.append(np.std(recalls_at_bp))
    
    mean_recall = np.array(mean_recall)
    std_recall = np.array(std_recall)
    
    if pol in main_policies:
        ax.plot(budget_points, mean_recall, label=label, color=color, linestyle=ls, linewidth=2.5)
        ax.fill_between(budget_points, mean_recall - std_recall, mean_recall + std_recall, 
                        color=color, alpha=0.15)
    else:
        ax.plot(budget_points, mean_recall, label=label, color=color, linestyle=ls, linewidth=1.8, alpha=0.8)

ax.axhline(y=n_high / n_mol * budget / budget, color='red', linestyle=':', alpha=0.5, 
           label=f'Random expectation line (1.0)')
ax.set_xlabel('Number of Molecules Queried', fontsize=13)
ax.set_ylabel('Recall (fraction of high-activity molecules found)', fontsize=13)
ax.set_title('BACE-1 Active Discovery: Surrogate vs. Random Selection', fontsize=14, fontweight='bold')
ax.legend(fontsize=11, loc='lower right')
ax.set_xlim(0, budget)
ax.set_ylim(0, 1.05)
ax.grid(True, alpha=0.3)

ax.annotate(f'Top 5% threshold: pIC50 ≥ {threshold:.2f}\n{n_high} high-activity molecules\n{initial_q} initial + {n_batches}×{batch_size} batches\nMean ± SD across {len(seeds)} seeds',
            xy=(0.98, 0.02), xycoords='axes fraction', fontsize=9,
            ha='right', va='bottom', 
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8))

plt.tight_layout()
plt.savefig('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/0d253518-3b38-4d96-aba9-4675f48f3fca/threads/fff9cae7-3467-496d-af05-0585c99fd993/user-data/outputs/active_discovery_recall_curve.png', dpi=200, bbox_inches='tight')
plt.close()
print("Saved active_discovery_recall_curve.png")

print("\n=== DONE ===")
