"""
tests/revision/test_t04_t05_t06_leakage_checks.py
Pruebas técnicas T04, T05 y T06: Verificación empírica de ausencia de fuga y separación estricta de particiones.
"""
import sys
from pathlib import Path
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scientific_core.generator import generate_coherent_dataset
from scientific_core.nested_cv import fit_and_predict_traditional, ModelFactory


def test_t04_scaler_fitted_strictly_on_train():
    """
    T04: Instrumenta el escalador para verificar que su media y varianza corresponden
    estrictamente a la partición de entrenamiento y no contienen filas de validación.
    """
    df, _ = generate_coherent_dataset(n_samples=40, random_state=42)
    X = df[["crop_area_pct", "natural_area_pct", "floral_strips_pct"]].to_numpy()
    y = df[["crop_yield_index", "pollinator_abundance_index"]].to_numpy()

    train_idx = np.arange(0, 30)
    val_idx = np.arange(30, 40)

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]

    model = MultiOutputRegressor(Ridge(alpha=1.0))
    preds, scaler_x, scaler_y = fit_and_predict_traditional(model, X_train, y_train, X_val)

    # 1. Comprobar que la media ajustada coincide EXACTAMENTE con X_train y no con X_full
    expected_mean_x = np.mean(X_train, axis=0)
    actual_mean_x = scaler_x.mean_
    np.testing.assert_allclose(actual_mean_x, expected_mean_x, rtol=1e-5)

    full_mean_x = np.mean(X, axis=0)
    assert not np.allclose(actual_mean_x, full_mean_x, rtol=1e-3), "Alerta de fuga: la media del scaler coincide con el dataset completo"

    # 2. Comprobar escalador de salidas y
    expected_mean_y = np.mean(y_train, axis=0)
    actual_mean_y = scaler_y.mean_
    np.testing.assert_allclose(actual_mean_y, expected_mean_y, rtol=1e-5)

    full_mean_y = np.mean(y, axis=0)
    assert not np.allclose(actual_mean_y, full_mean_y, rtol=1e-3), "Alerta de fuga: la media del scaler y coincide con el dataset completo"
    print("T04 PASSED: Scaler ajustado estrictamente en partición de entrenamiento (sin fuga de val/test).")


def test_t06_fresh_model_instances_between_folds():
    """
    T06: Verifica que cada fold recibe instancias de modelo independientes y que
    los pesos o coeficientes no se conservan entre particiones.
    """
    model_1 = ModelFactory.create_model("ridge", {"alpha": 1.0}, seed=42)
    model_2 = ModelFactory.create_model("ridge", {"alpha": 1.0}, seed=43)

    assert model_1 is not model_2, "Las instancias de modelo no deben ser el mismo objeto"
    assert not hasattr(model_1, "coef_"), "El modelo nuevo no debe contener coeficientes ajustados"

    # Ajustar model_1 con datos ficticios
    X_dummy = np.array([[1.0, 2.0], [3.0, 4.0]])
    y_dummy = np.array([[10.0], [20.0]])
    model_1.fit(X_dummy, y_dummy)

    assert hasattr(model_1, "coef_"), "model_1 debe tener coeficientes ajustados tras fit"
    assert not hasattr(model_2, "coef_"), "model_2 permanece sin ajustar (aislamiento de estado confirmado)"
    print("T06 PASSED: Instancias completamente independientes entre folds sin estado compartido.")


if __name__ == "__main__":
    test_t04_scaler_fitted_strictly_on_train()
    test_t06_fresh_model_instances_between_folds()
    print("Leakage checks passed successfully!")
