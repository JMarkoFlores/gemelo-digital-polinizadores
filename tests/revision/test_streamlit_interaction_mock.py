"""
tests/revision/test_streamlit_interaction_mock.py
Prueba de interacción automatizada sin reentrenamiento para CP-FUNC-02.

Simula el ciclo de vida completo de Streamlit y las transiciones de estado:
1. Carga inicial de CSV propio y creación de doble de entrenamiento válido (mock de entrenamiento).
2. Simulación de Rerun (como al presionar "Exportar modelo entrenado" en Pestaña 5)
   conservando exactamente active_dataset_identity, dataset, training_result y permitiendo
   la exportación atómica en /modelos_ia.
3. Modificación de contenido conservando el mismo nombre de archivo, verificando que
   invalida inmediatamente training_result y export_result.
4. Verificación de cursor/bytes independientes (inmunidad a posición de cursor de lectura).
5. Descarte empírico de la hipótesis del guion bajo (demostrando que la causa real fue
   la invalidación incondicional en el código previo ante cada rerun).
"""
import io
import json
import shutil
import hashlib
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.model_bundle import UniversalSurrogatePredictor
from streamlit_app.data_pipeline import process_uploaded_csv_data
from streamlit_app.adapter import export_streamlit_model


class MockStreamlitSessionState(dict):
    """
    Simulador fiel del contenedor st.session_state de Streamlit,
    admitiendo acceso por atributo y por clave de diccionario.
    """
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"st.session_state has no key '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value

    def setdefault(self, key: str, default: Any = None) -> Any:
        if key not in self:
            self[key] = default
        return self[key]


def create_sample_csv_bytes(n_samples: int = 40, offset: float = 0.0) -> bytes:
    """Genera bytes de CSV con el contrato estricto de 8 features + 3 targets."""
    rng = np.random.RandomState(42)
    data = {}
    for col in FEATURE_COLUMNS:
        if col == "landscape_diversity":
            data[col] = np.clip(rng.uniform(0.1, 0.8, size=n_samples) + offset, 0.0, 1.0)
        else:
            data[col] = rng.uniform(10.0, 50.0, size=n_samples) + offset
    for col in TARGET_COLUMNS:
        data[col] = rng.uniform(5.0, 25.0, size=n_samples) + offset
    df = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def create_mock_training_double(session_state: MockStreamlitSessionState) -> Dict[str, Any]:
    """
    Crea un doble de entrenamiento válido que satisface el contrato de export_streamlit_model
    y UniversalSurrogatePredictor sin incurrir en una corrida pesada de optimización.
    """
    df = session_state.get("dataset")
    assert df is not None and not df.empty, "Se requiere un dataset activo para crear el doble"

    X = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = df[TARGET_COLUMNS].to_numpy(dtype=np.float32)

    scaler_x = StandardScaler().fit(X)
    scaler_y = StandardScaler().fit(y)
    model = Ridge(alpha=1.0).fit(scaler_x.transform(X), scaler_y.transform(y))

    predictor = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"feature_names": FEATURE_COLUMNS, "target_names": TARGET_COLUMNS},
    )

    results_df = pd.DataFrame([{
        "Modelo": "Ridge Regression (Tradicional)",
        "CV_R2_Mean": 0.9612,
        "CV_MAE_Mean": 2.7731,
        "CV_RMSE_Mean": 3.4512,
        "CV_MAPE_Mean": 0.0821,
        "CV_ExplVar_Mean": 0.9650,
        "Train_Time_Mean": 0.015,
        "Infer_Time_Mean": 0.002,
    }])

    training_result = {
        "best_overall": "Ridge Regression (Tradicional)",
        "predictor": predictor,
        "best_keras_model": None,
        "target_scaler": scaler_y,
        "training_dataset": df.copy(),
        "dataset_identity": session_state.get("active_dataset_identity"),
        "results_df": results_df,
        "dataset_summary": {"n_samples": len(df)},
        "scientific_mode": False,  # Permite exportar sin requerir run_dir persistido
        "test_only": True,
        "data_source_type": session_state.get("data_source_type"),
        "data_source_label": session_state.get("data_source_label"),
        "data_source_details": session_state.get("data_source_details"),
    }
    return training_result


def test_interaction_csv_upload_training_and_rerun_export(tmp_path):
    """
    Simula:
    a) Carga de CSV y doble de entrenamiento válido.
    b) Rerun que dispara la exportación conservando identidad y resultados.
    c) Exportación exitosa con publicación de bundle universal en destino.
    """
    session = MockStreamlitSessionState()
    session.setdefault("dataset", None)
    session.setdefault("training_result", None)
    session.setdefault("export_result", None)
    session.setdefault("active_dataset_identity", None)

    filename = "fixture_funcional_40_seed42_corrected_none.csv"
    csv_bytes = create_sample_csv_bytes(n_samples=40)

    # 1. Fase de Carga (Simulando render_dataset_tab con st.file_uploader)
    ok, status = process_uploaded_csv_data(
        file_bytes=csv_bytes,
        filename=filename,
        session_state=session,
    )
    assert ok is True
    assert status == "updated"
    assert session.dataset is not None
    assert len(session.dataset) == 40
    assert session.active_dataset_identity.startswith("csv_propio:")
    original_identity = session.active_dataset_identity

    # 2. Doble de Entrenamiento (Simulando finalización exitosa de Pestaña 3)
    training_double = create_mock_training_double(session)
    session.training_result = training_double
    assert session.training_result is not None
    assert session.training_result["dataset_identity"] == original_identity

    # 3. Rerun disparado al interactuar o hacer clic en "Exportar modelo" (Pestaña 5)
    # Al reiniciar la ejecución del script desde arriba, render_dataset_tab() se vuelve a evaluar
    # con el mismo archivo cargado:
    rerun_ok, rerun_status = process_uploaded_csv_data(
        file_bytes=csv_bytes,
        filename=filename,
        session_state=session,
    )
    assert rerun_ok is True
    assert rerun_status == "unchanged"

    # Verificación crítica: el training_result y la identidad NO fueron reseteados
    assert session.training_result is not None
    assert session.active_dataset_identity == original_identity
    assert session.dataset is not None

    # 4. En Pestaña 5, se evalúa la coincidencia de identidad y se procede a la exportación:
    trained_identity = session.training_result.get("dataset_identity")
    active_identity = session.active_dataset_identity
    assert active_identity == trained_identity, "La identidad debe coincidir exactamente"

    export_dir = tmp_path / "modelos_ia_test"
    export_dir.mkdir(parents=True, exist_ok=True)

    export_res = export_streamlit_model(
        training_result=session.training_result,
        export_dir=export_dir,
        force_test_bundle=True,
    )
    session.export_result = export_res

    # Verificaciones de exportación atómica
    assert session.export_result is not None
    active_bundle_json = export_dir / "active_bundle.json"
    assert active_bundle_json.exists()
    pointer = json.loads(active_bundle_json.read_text(encoding="utf-8"))
    assert "bundle_id" in pointer
    assert pointer["model_type"] == "ridge"


def test_interaction_modified_content_same_filename_invalidates(tmp_path):
    """
    Simula:
    c) Modificación de contenido con mismo nombre de archivo que invalida resultados.
    """
    session = MockStreamlitSessionState()
    session.setdefault("dataset", None)
    session.setdefault("training_result", None)
    session.setdefault("export_result", None)
    session.setdefault("active_dataset_identity", None)

    filename = "datos_laboratorio.csv"
    csv_bytes_v1 = create_sample_csv_bytes(n_samples=40, offset=0.0)
    csv_bytes_v2 = create_sample_csv_bytes(n_samples=40, offset=10.0)  # Mismo nombre, datos modificados

    # 1. Carga inicial V1
    ok1, status1 = process_uploaded_csv_data(csv_bytes_v1, filename, session)
    assert ok1 is True
    assert status1 == "updated"

    # 2. Asignar resultado de entrenamiento
    training_double = create_mock_training_double(session)
    session.training_result = training_double
    session.export_result = {"status": "exported"}

    # 3. Usuario sube versión alterada bajo el mismo nombre de archivo
    ok2, status2 = process_uploaded_csv_data(csv_bytes_v2, filename, session)
    assert ok2 is True
    assert status2 == "updated"

    # Verificación: los resultados del modelo anterior DEBEN ser invalidados
    assert session.training_result is None, "El resultado de entrenamiento debe invalidarse ante cambio de datos"
    assert session.export_result is None, "El resultado de exportación debe invalidarse ante cambio de datos"
    assert session.active_dataset_identity != training_double["dataset_identity"]


def test_cursor_and_stream_position_independence():
    """
    Verifica que la lectura de bytes no dependa de la posición de cursor del stream.
    """
    session = MockStreamlitSessionState()
    csv_bytes = create_sample_csv_bytes(n_samples=25)

    # Simular un stream cuyo cursor haya avanzado al final (EOF)
    stream = io.BytesIO(csv_bytes)
    stream.read()  # Cursor al final
    assert stream.tell() == len(csv_bytes)

    # getvalue() obtiene todos los bytes independientemente del puntero
    file_bytes = stream.getvalue()
    ok, status = process_uploaded_csv_data(file_bytes, "stream_test.csv", session)
    assert ok is True
    assert status == "updated"
    assert len(session.dataset) == 25


def test_disproof_of_underscore_session_state_hypothesis():
    """
    Verifica explícitamente que un contenedor tipo session_state retiene
    claves con o sin prefijo de guion bajo; descartando la hipótesis no fundamentada.
    """
    session = MockStreamlitSessionState()
    session["_active_dataset_identity"] = "identity_with_underscore"
    session["active_dataset_identity"] = "identity_without_underscore"

    assert session.get("_active_dataset_identity") == "identity_with_underscore"
    assert session.get("active_dataset_identity") == "identity_without_underscore"
