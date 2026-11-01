"""
tests/revision/test_true_provenance.py
Verificación del Mandato 8: Procedencia veraz de datos e integridad de versionado.
Comprueba que:
  1. Las variables climáticas generadas sintéticamente no se etiquetan falsamente como NASA POWER por su nombre de columna.
  2. La procedencia real exige evidencia de generación o snapshot criptográfico de importación.
  3. El versionado explícito v2_corrected se preserva registrando sus diferencias con v1_historical.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scientific_core.data_audit import audit_dataset, classify_column_provenance
from scientific_core.generator import generate_coherent_dataset


def test_synthetic_data_not_attributed_to_nasa_power():
    """Verifica que un dataset sintético declare procedencia sintética sin claims de NASA POWER."""
    df, meta = generate_coherent_dataset(n_samples=25, random_state=42)
    assert meta["generator_version"] == "v2_corrected"
    assert meta["historical_version_preserved"] == "v1_historical"
    assert meta["source_type"] == "sintetico_generado"
    assert meta["real_data_attributions"] is False

    audit_res = audit_dataset(df, source_metadata=meta)
    col_prov = audit_res["column_provenance"]

    # Comprobar que temperature_c y precipitation_mm NO dicen nasa_power
    assert col_prov["temperature_c"] == "variable_climatica_sintetica_calibrada"
    assert col_prov["precipitation_mm"] == "variable_climatica_sintetica_calibrada"
    assert "nasa_power" not in col_prov["temperature_c"]
    print("PASS: Variables sintéticas no atribuidas indebidamente a NASA POWER.")


def test_real_provenance_with_snapshot_evidence():
    """Verifica que la procedencia pública sólo se asigne cuando exista evidencia explícita."""
    verified_meta = {
        "fuente_datos": "publico_gbif_nasa_power",
        "nasa_power_verified": True,
        "snapshot_sha256": "abcdef1234567890",
        "gbif_verified": True,
        "gbif_snapshot_sha256": "fedcba0987654321",
    }

    prov_temp = classify_column_provenance("temperature_c", verified_meta)
    assert prov_temp == "dato_publico_nasa_power_verificado"

    prov_abund = classify_column_provenance("pollinator_abundance_index", verified_meta)
    assert prov_abund == "indice_hibrido_gbif_abm"
    print("PASS: Procedencia verificada asignada exclusivamente ante evidencia documental.")


if __name__ == "__main__":
    test_synthetic_data_not_attributed_to_nasa_power()
    test_real_provenance_with_snapshot_evidence()
