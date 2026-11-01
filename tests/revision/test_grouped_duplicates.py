"""
tests/revision/test_grouped_duplicates.py
Verificación del Mandato 5: Agrupamiento real de duplicados (GroupKFold) en Nested CV.
Demuestra que:
  1. Filas con características idénticas pero IDs distintos y etiquetas diferentes
     se asignan al mismo grupo.
  2. Ningún grupo de características cruza entre particiones de entrenamiento y test
     en ningún fold externo ni interno.
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.nested_cv import compute_feature_groups, run_nested_cv


def test_grouped_duplicates_zero_leakage():
    """
    Crea un dataset con duplicados exactos en características pero IDs distintos,
    y verifica que ningún grupo cruce entre entrenamiento y evaluación.
    """
    rng = np.random.default_rng(100)
    n_unique_scenarios = 15
    n_replicates_per_scenario = 3
    total_samples = n_unique_scenarios * n_replicates_per_scenario  # 45 muestras

    # Generar 15 escenarios base únicos
    base_features = rng.uniform(10.0, 50.0, size=(n_unique_scenarios, len(FEATURE_COLUMNS)))

    rows = []
    sample_id = 1
    for scen_idx in range(n_unique_scenarios):
        feat_row = base_features[scen_idx]
        for rep in range(n_replicates_per_scenario):
            # Mismas características de entrada, pero con variación estocástica en salida (ej. réplicas ABM)
            target_vals = [
                float(feat_row[0] * 1.5 + rng.normal(0, 1.0)),
                float(feat_row[1] * 2.0 + rng.normal(0, 1.0)),
                float(feat_row[2] * 0.8 + rng.normal(0, 0.5)),
            ]
            row_dict = {
                "sample_id": sample_id,
                **{col: float(feat_row[i]) for i, col in enumerate(FEATURE_COLUMNS)},
                **{t_col: target_vals[i] for i, t_col in enumerate(TARGET_COLUMNS)},
            }
            rows.append(row_dict)
            sample_id += 1

    df = pd.DataFrame(rows)
    assert len(df) == 45
    assert df["sample_id"].nunique() == 45  # IDs todos distintos

    # Verificar cálculo de grupos
    X = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    groups = compute_feature_groups(X)
    assert len(np.unique(groups)) == 15, "Deben existir exactamente 15 grupos de características."

    config = {
        "outer_cv": {"n_splits": 5, "seed": 42, "group_duplicates": True},
        "inner_cv": {"n_splits": 2, "seed": 1042},
        "models": {
            "ridge": {"enabled": True, "param_grid": [{"alpha": 1.0}]},
        },
    }

    cv_res = run_nested_cv(df, config)
    splits_manifest = cv_res["splits_manifest"]

    assert splits_manifest["group_duplicates_applied"] is True
    assert splits_manifest["n_unique_feature_groups"] == 15

    # Comprobar disyunción estricta de grupos en cada fold externo
    for fold_info in splits_manifest["outer_folds"]:
        train_ids = fold_info["train_sample_ids"]
        test_ids = fold_info["test_sample_ids"]

        train_mask = df["sample_id"].isin(train_ids)
        test_mask = df["sample_id"].isin(test_ids)

        train_groups = set(groups[train_mask])
        test_groups = set(groups[test_mask])

        # Ningún grupo puede aparecer en ambos conjuntos
        intersection = train_groups.intersection(test_groups)
        assert len(intersection) == 0, (
            f"Fuga detectada en fold {fold_info['outer_fold']}: "
            f"los grupos {intersection} aparecen tanto en entrenamiento como en test!"
        )

    print("PASS: test_grouped_duplicates_zero_leakage (0% fuga demostrada entre réplicas)")


if __name__ == "__main__":
    test_grouped_duplicates_zero_leakage()
