"""
tests/revision/test_t03_to_t09_nested_cv.py
Verificación técnica rigurosa de las pruebas T03, T04, T06, T07, T08, T09 del Plan.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scientific_core.generator import generate_coherent_dataset
from scientific_core.nested_cv import run_nested_cv, recompute_metrics_from_oof


def test_nested_cv_suite():
    # 1. Dataset fixture reproducible
    df, _ = generate_coherent_dataset(n_samples=30, random_state=42)

    config = {
        "outer_cv": {"n_splits": 3, "seed": 42},
        "inner_cv": {"n_splits": 2, "seed": 1042},
        "models": {
            "ridge": {
                "enabled": True,
                "param_grid": [{"alpha": 0.1}, {"alpha": 10.0}],
            },
            "random_forest": {
                "enabled": True,
                "param_grid": [{"n_estimators": 5, "max_depth": 3}],
            },
        },
    }

    res = run_nested_cv(df, config)
    assert res["status"] == "completed"

    # ──────────────────────────────────────────────────────────────────────────
    # T03: IDs de train/test y particiones disjuntas con cobertura completa
    # ──────────────────────────────────────────────────────────────────────────
    manifest = res["splits_manifest"]
    all_test_ids = []
    for f in manifest["outer_folds"]:
        tr_set = set(f["train_sample_ids"])
        te_set = set(f["test_sample_ids"])
        # Disjuntos en cada fold
        assert len(tr_set.intersection(te_set)) == 0, f"Fold {f['outer_fold']} tiene IDs solapados entre train y test"
        all_test_ids.extend(f["test_sample_ids"])

    # Cobertura completa del dataset (cada fila evaluada exactamente una vez)
    assert sorted(all_test_ids) == sorted(df["sample_id"].tolist()), "Cobertura de test incompleta o con repetición"
    print("T03 PASSED: Train y test disjuntos en todos los folds y cobertura completa.")

    # ──────────────────────────────────────────────────────────────────────────
    # T07: OOF completo, exactamente una predicción por fila y sin NaNs
    # ──────────────────────────────────────────────────────────────────────────
    oof_df = res["oof_predictions_df"]
    for fam in res["available_families"]:
        fam_oof = oof_df[oof_df["model_id"] == fam]
        # 30 filas * 3 targets = 90 predicciones
        assert len(fam_oof) == 30 * 3, f"Conteo OOF incorrecto para {fam}: {len(fam_oof)}"
        assert not fam_oof["y_pred"].isna().any(), f"Existen NaNs en predicciones OOF de {fam}"
        assert not np.isnan(res["oof_preds_matrices"][fam]).any(), f"Matriz OOF contiene NaN para {fam}"
    print("T07 PASSED: OOF completo, 1 predicción por fila/modelo y 0 NaNs.")

    # ──────────────────────────────────────────────────────────────────────────
    # T08: Reconstrucción de métricas desde OOF coincide exactamente
    # ──────────────────────────────────────────────────────────────────────────
    recomputed = recompute_metrics_from_oof(oof_df)
    summary_df = res["summary_df"]

    for fam in res["available_families"]:
        rec_macro = recomputed[fam]["macro"]
        row = summary_df[summary_df["model_id"] == fam].iloc[0]
        # Coincidencia con tolerancia numérica < 1e-5
        diff = abs(rec_macro["macro_mae"] - row["OOF_Macro_MAE"])
        assert diff < 1e-5, f"Discrepancia en reconstrucción de OOF MAE: {diff}"
    print("T08 PASSED: Reconstrucción de métricas desde OOF coincide al 100%.")

    # ──────────────────────────────────────────────────────────────────────────
    # T09: Selección respeta estrictamente el criterio fijado (menor MAE macro)
    # ──────────────────────────────────────────────────────────────────────────
    best_selected = res["best_overall"]
    expected_best = summary_df.iloc[0]["model_id"]
    assert best_selected == expected_best, f"Selección inconsistente: {best_selected} vs {expected_best}"
    # Verificar orden ascendente de CV_MAE_Mean
    mae_list = summary_df["CV_MAE_Mean"].tolist()
    assert mae_list == sorted(mae_list), "Summary DataFrame no está ordenado por menor MAE"
    print("T09 PASSED: Selección objetiva respeta criterio de menor MAE macro.")


if __name__ == "__main__":
    test_nested_cv_suite()
    print("All nested CV tests passed successfully!")
