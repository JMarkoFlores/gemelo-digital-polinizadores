"""
scientific_core
Paquete central de contratos científicos, auditoría, generador y evaluación metodológica.
"""
from scientific_core.contracts import (
    FEATURE_COLUMNS,
    TARGET_COLUMNS,
    FEATURE_BOUNDS,
    TARGET_BOUNDS,
    calculate_landscape_diversity,
    validate_coverage,
    repair_coverage,
    check_feature_bounds,
)
try:
    from scientific_core.data_audit import audit_dataset, compute_file_sha256, compute_dataframe_sha256
    from scientific_core.generator import generate_coherent_dataset
except ImportError:
    from scientific_core.data_audit import compute_file_sha256
    audit_dataset = None
    compute_dataframe_sha256 = None
    generate_coherent_dataset = None

__all__ = [
    "FEATURE_COLUMNS",
    "TARGET_COLUMNS",
    "FEATURE_BOUNDS",
    "TARGET_BOUNDS",
    "calculate_landscape_diversity",
    "validate_coverage",
    "repair_coverage",
    "check_feature_bounds",
    "audit_dataset",
    "compute_file_sha256",
    "compute_dataframe_sha256",
    "generate_coherent_dataset",
]
