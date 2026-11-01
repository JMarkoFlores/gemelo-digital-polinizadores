import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

base_dir = Path("artifacts/revision_metodologica/campana_cientifica")
run_dir = base_dir / "run_20261029_153857"

oof_df = pd.read_csv(run_dir / "oof_predictions.csv")
fold_df = pd.read_csv(run_dir / "fold_metrics.csv")
tuning_df = pd.read_csv(run_dir / "tuning_results.csv")
model_summary = pd.read_csv(run_dir / "model_summary.csv")

# 1. Tabla detallada por modelo y objetivo
families = ["ridge", "dnn", "autoencoder_mlp", "xgboost", "random_forest"]
targets = ["crop_yield_index", "pollinator_abundance_index", "pollinator_diversity_index"]

rows = []
for fam in families:
    sub_oof = oof_df[oof_df["model_id"] == fam]
    sub_fold = fold_df[(fold_df["model_id"] == fam) & (fold_df["target"] == "macro_average")]
    
    # OOF global per target
    t_maes = {}
    t_rmses = {}
    t_r2s = {}
    for t in targets:
        t_sub = sub_oof[sub_oof["target"] == t]
        t_maes[t] = mean_absolute_error(t_sub["y_true"], t_sub["y_pred"])
        t_rmses[t] = np.sqrt(mean_squared_error(t_sub["y_true"], t_sub["y_pred"]))
        t_r2s[t] = r2_score(t_sub["y_true"], t_sub["y_pred"])
        
    global_macro_mae = np.mean(list(t_maes.values()))
    global_macro_rmse = np.mean(list(t_rmses.values()))
    global_macro_r2 = np.mean(list(t_r2s.values()))
    
    cv_macro_mae_mean = sub_fold["mae"].mean()
    cv_macro_mae_std = sub_fold["mae"].std()
    cv_macro_rmse_mean = sub_fold["rmse"].mean()
    cv_macro_rmse_std = sub_fold["rmse"].std()
    cv_macro_r2_mean = sub_fold["r2"].mean()
    cv_macro_r2_std = sub_fold["r2"].std()
    
    train_t = sub_fold["train_time_seconds"].mean()
    infer_t = sub_fold["infer_time_seconds"].mean()
    
    rows.append({
        "family": fam,
        "cv_macro_mae_mean": cv_macro_mae_mean,
        "cv_macro_mae_std": cv_macro_mae_std,
        "cv_macro_rmse_mean": cv_macro_rmse_mean,
        "cv_macro_rmse_std": cv_macro_rmse_std,
        "cv_macro_r2_mean": cv_macro_r2_mean,
        "cv_macro_r2_std": cv_macro_r2_std,
        "oof_macro_mae": global_macro_mae,
        "oof_macro_rmse": global_macro_rmse,
        "oof_macro_r2": global_macro_r2,
        "yield_mae": t_maes["crop_yield_index"],
        "abundance_mae": t_maes["pollinator_abundance_index"],
        "diversity_mae": t_maes["pollinator_diversity_index"],
        "yield_r2": t_r2s["crop_yield_index"],
        "abundance_r2": t_r2s["pollinator_abundance_index"],
        "diversity_r2": t_r2s["pollinator_diversity_index"],
        "mean_train_time_s": train_t,
        "mean_infer_time_s": infer_t,
    })

df_table1 = pd.DataFrame(rows)
df_table1.to_csv(base_dir / "tabla_comparativa_modelos.csv", index=False)
print("Saved tabla_comparativa_modelos.csv")

# 2. Generar Figuras de calidad para artículo
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

# Figura 1: Barras de Macro MAE
fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
colors = ['#2b5c8f', '#4682b4', '#5f9ea0', '#e07a5f', '#d9534f']
bars = ax.bar(df_table1['family'], df_table1['cv_macro_mae_mean'], yerr=df_table1['cv_macro_mae_std'], 
              capsize=5, color=colors, edgecolor='black', alpha=0.85, width=0.55)
ax.set_ylabel('Macro MAE (Escala Original)', fontsize=12, fontweight='bold')
ax.set_title('Evaluación Predictiva Multimodelo: Macro MAE en Validación Cruzada Anidada (5x3 Folds)', 
             fontsize=13, fontweight='bold', pad=15)
ax.set_ylim(0, 4.0)

for bar in bars:
    yval = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.15, f"{yval:.3f}", ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
fig.savefig(base_dir / "figura_1_comparativa_macro_mae.png")
plt.close()
print("Saved figura_1_comparativa_macro_mae.png")

# Figura 2: Dispersión OOF Ridge (Ganador)
fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), dpi=300)
ridge_oof = oof_df[oof_df["model_id"] == "ridge"]

titles = ["Rendimiento de Cultivo", "Abundancia de Polinizadores", "Diversidad de Polinizadores"]
target_keys = ["crop_yield_index", "pollinator_abundance_index", "pollinator_diversity_index"]

for i, (t_key, t_title) in enumerate(zip(target_keys, titles)):
    sub = ridge_oof[ridge_oof["target"] == t_key]
    ax = axes[i]
    ax.scatter(sub["y_true"], sub["y_pred"], alpha=0.6, edgecolors='none', color='#2b5c8f', s=25)
    min_v = min(sub["y_true"].min(), sub["y_pred"].min())
    max_v = max(sub["y_true"].max(), sub["y_pred"].max())
    ax.plot([min_v, max_v], [min_v, max_v], 'r--', lw=1.5, label='1:1 Ideal')
    r2_v = r2_score(sub["y_true"], sub["y_pred"])
    mae_v = mean_absolute_error(sub["y_true"], sub["y_pred"])
    ax.set_title(f"{t_title}\n$R^2={r2_v:.3f}$ | MAE$={mae_v:.2f}$", fontsize=11, fontweight='bold')
    ax.set_xlabel('Valor Simulado Real (True)', fontsize=10)
    ax.set_ylabel('Predicción Sustituto OOF (Pred)', fontsize=10)
    ax.legend(loc='upper left', fontsize=9)

plt.suptitle('Calidad Predictiva Out-Of-Fold (OOF) del Sustituto Ganador (Ridge, $\\alpha=0.1$)', fontsize=13, fontweight='bold', y=1.03)
plt.tight_layout()
fig.savefig(base_dir / "figura_2_oof_dispersion_ridge.png")
plt.close()
print("Saved figura_2_oof_dispersion_ridge.png")
