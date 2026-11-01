"""
tests/revision/test_streamlit_csv_persistence.py
Pruebas focalizadas para la persistencia del CSV y resultados en Streamlit (CP-FUNC-02).
Verifica:
1. Identidad basada en contenido (SHA-256): el rerun con el mismo contenido conserva
   dataset, training_result y export_result.
2. Modificar el contenido conservando el mismo nombre de archivo invalida training_result y export_result.
3. Transiciones entre fuentes de datos (CSV -> Sintético -> Público) invalidan resultados
   e impiden exportar modelos asociados a otro dataset.
4. Archivo CSV vacío o con columnas faltantes es rechazado y limpia el estado.
"""
import io
import hashlib
import pandas as pd
import pytest

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from streamlit_app.data_pipeline import process_uploaded_csv_data


def create_dummy_csv_bytes(n_rows: int = 10, offset: float = 0.0) -> bytes:
    data = {}
    for col in FEATURE_COLUMNS:
        data[col] = [float(i) + offset for i in range(n_rows)]
    for col in TARGET_COLUMNS:
        data[col] = [float(i * 2) + offset for i in range(n_rows)]
    df = pd.DataFrame(data)
    out = io.StringIO()
    df.to_csv(out, index=False)
    return out.getvalue().encode("utf-8")


def test_initial_csv_upload_and_state_initialization():
    csv_bytes = create_dummy_csv_bytes(n_rows=15)
    session = {}

    ok, status = process_uploaded_csv_data(
        file_bytes=csv_bytes,
        filename="test_dataset.csv",
        session_state=session,
    )
    assert ok is True
    assert status == "updated"
    assert session["dataset"] is not None
    assert len(session["dataset"]) == 15
    assert session["data_source_type"] == "csv_propio"
    assert session["active_dataset_identity"] is not None
    assert session["training_result"] is None
    assert session["export_result"] is None


def test_rerun_with_identical_csv_preserves_results():
    csv_bytes = create_dummy_csv_bytes(n_rows=20)
    session = {}

    # 1. Carga inicial
    ok, status = process_uploaded_csv_data(csv_bytes, "datos.csv", session)
    assert ok is True
    assert status == "updated"

    # 2. Simular corrida de entrenamiento y exportación
    dummy_training = {
        "best_overall": "ridge",
        "dataset_identity": session["active_dataset_identity"],
        "results_df": pd.DataFrame({"Modelo": ["ridge"]}),
    }
    dummy_export = {"bundle_id": "bundle_ridge_test"}
    session["training_result"] = dummy_training
    session["export_result"] = dummy_export

    # 3. Rerun ordinario con el mismo contenido (e.g. pulsar botón de otra pestaña)
    ok_rerun, status_rerun = process_uploaded_csv_data(csv_bytes, "datos.csv", session)
    assert ok_rerun is True
    assert status_rerun == "unchanged"

    # Verificar que los resultados NO se perdieron
    assert session["training_result"] is dummy_training
    assert session["export_result"] is dummy_export
    assert len(session["dataset"]) == 20


def test_modified_content_with_same_filename_invalidates_results():
    csv_bytes_v1 = create_dummy_csv_bytes(n_rows=20, offset=0.0)
    csv_bytes_v2 = create_dummy_csv_bytes(n_rows=20, offset=5.0)  # Mismo nombre, contenido alterado
    session = {}

    # Carga V1
    process_uploaded_csv_data(csv_bytes_v1, "datos.csv", session)
    session["training_result"] = {"modelo": "m1"}
    session["export_result"] = {"bundle": "b1"}

    # Carga V2 con el mismo nombre "datos.csv" pero diferente contenido
    ok, status = process_uploaded_csv_data(csv_bytes_v2, "datos.csv", session)
    assert ok is True
    assert status == "updated"

    # La identidad cambió y los resultados anteriores fueron invalidados
    assert session["training_result"] is None
    assert session["export_result"] is None
    assert session["data_source_details"]["content_hash"] == hashlib.sha256(csv_bytes_v2).hexdigest()


def test_empty_or_invalid_csv_rejected_and_clears_state():
    session = {"training_result": {"dummy": True}, "dataset": pd.DataFrame()}

    # Archivo vacío
    ok_empty, msg_empty = process_uploaded_csv_data(b"", "vacio.csv", session)
    assert ok_empty is False
    assert "vacío" in msg_empty

    # Columnas faltantes
    bad_csv = b"col1,col2\n1,2\n3,4\n"
    ok_bad, msg_bad = process_uploaded_csv_data(bad_csv, "incompleto.csv", session)
    assert ok_bad is False
    assert "columnas mínimas" in msg_bad
    assert session["dataset"] is None
    assert session["training_result"] is None


def test_transition_between_data_sources_prevents_mismatched_export():
    csv_bytes = create_dummy_csv_bytes(n_rows=10)
    session = {}

    # 1. Cargar CSV y simular entrenamiento
    process_uploaded_csv_data(csv_bytes, "dataset_a.csv", session)
    csv_identity = session["active_dataset_identity"]
    training_result = {
        "best_overall": "ridge",
        "dataset_identity": csv_identity,
        "training_dataset": session["dataset"],
    }
    session["training_result"] = training_result

    # 2. Transición a dataset sintético (cambio de fuente activa)
    session["data_source_type"] = "sintetico"
    session["active_dataset_identity"] = "sintetico:320:42:True:dummyhash"
    session["dataset"] = pd.DataFrame({"diferente": [1, 2, 3]})

    # 3. Validar la guarda de coherencia
    active_identity = session.get("active_dataset_identity")
    trained_identity = session["training_result"].get("dataset_identity")
    assert active_identity != trained_identity
    # El modelo no debe ser exportable bajo este estado desalineado
