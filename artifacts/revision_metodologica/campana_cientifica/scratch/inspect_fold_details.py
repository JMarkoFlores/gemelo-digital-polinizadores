import pandas as pd
import json

fold_df = pd.read_csv('artifacts/revision_metodologica/campana_cientifica/run_20261029_153857/fold_metrics.csv')
tuning_df = pd.read_csv('artifacts/revision_metodologica/campana_cientifica/run_20261029_153857/tuning_results.csv')
splits_json = json.load(open('artifacts/revision_metodologica/campana_cientifica/run_20261029_153857/splits.json', 'r', encoding='utf-8'))
manifest = json.load(open('artifacts/revision_metodologica/campana_cientifica/run_20261029_153857/manifest.json', 'r', encoding='utf-8'))

print("=== FOLD MACRO METRICS SUMMARY ===")
macro_folds = fold_df[fold_df['target'] == 'macro_average']
print(macro_folds[['outer_fold', 'model_id', 'mae', 'rmse', 'r2', 'train_time_seconds', 'infer_time_seconds']].to_string())

print("\n=== TUNING RESULTS: SELECTED CANDIDATES PER OUTER FOLD ===")
# For each outer fold and family, show the winning candidate
for of in range(5):
    print(f"\n--- Outer Fold {of} ---")
    sub_of = tuning_df[tuning_df['outer_fold'] == of]
    for fam in ['ridge', 'random_forest', 'xgboost', 'dnn', 'autoencoder_mlp']:
        fam_sub = sub_of[sub_of['model_family'] == fam]
        best_cand = fam_sub.sort_values(['inner_macro_mae', 'inner_macro_rmse']).iloc[0]
        print(f"  {fam:16s}: MAE_in={best_cand['inner_macro_mae']:.4f}, RMSE_in={best_cand['inner_macro_rmse']:.4f}, params={best_cand['params']}")

print("\n=== GLOBAL WINNING HYPERPARAMS ACROSS ALL INNER CV EVALS ===")
# Aggregate across all outer folds for final refit
for fam in ['ridge', 'random_forest', 'xgboost', 'dnn', 'autoencoder_mlp']:
    fam_sub = tuning_df[tuning_df['model_family'] == fam]
    agg = fam_sub.groupby('params').agg({'inner_macro_mae': 'mean', 'inner_macro_rmse': 'mean'}).reset_index()
    agg = agg.sort_values(['inner_macro_mae', 'inner_macro_rmse'])
    winner = agg.iloc[0]
    print(f"  {fam:16s}: Mean Inner MAE={winner['inner_macro_mae']:.4f}, Mean Inner RMSE={winner['inner_macro_rmse']:.4f}, params={winner['params']}")
