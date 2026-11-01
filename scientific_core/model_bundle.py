"""
scientific_core/model_bundle.py
Gestión del bundle universal desacoplado para cualquier familia de modelo sustituto
(Scikit-Learn, XGBoost, Keras DNN y Keras Autoencoder/Bottleneck MLP).
Garantiza:
  1. Contrato único de preprocesamiento (scaler_x y scaler_y aplicados de manera idéntica
     a Ridge, Random Forest, XGBoost y Redes Neuronales sin excepciones por nombre).
  2. Verificación rigurosa de orden y coincidencia exacta de características y targets.
  3. Verificación de integridad criptográfica SHA-256 de todos los componentes del bundle.
  4. Rechazo estricto si faltan transformadores obligatorios (como scalers.pkl).
  5. Exportación atómica: escritura en directorio temporal, autovalidación de inferencia y movimiento seguro.
  6. Identificador de bundle (bundle_id) persistente y trazable.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
from pathlib import Path
import pickle
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
try:
    import pandas as pd
except ImportError:
    pd = None
from sklearn.preprocessing import StandardScaler

from scientific_core.contracts import (
    FEATURE_COLUMNS,
    TARGET_COLUMNS,
    PHYSICAL_BOUNDS,
)
from scientific_core.data_audit import compute_file_sha256

logger = logging.getLogger(__name__)

try:
    import tensorflow as tf
except ImportError:
    tf = None


class UniversalSurrogatePredictor:
    """
    Predictor universal para inferencia multi-salida con preprocesamiento explícito y verificado.
    """

    def __init__(
        self,
        model: Any,
        model_type: str,
        scaler_x: Optional[StandardScaler] = None,
        scaler_y: Optional[StandardScaler] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.model = model
        self.model_type = model_type
        self.scaler_x = scaler_x
        self.scaler_y = scaler_y
        self.metadata = metadata or {}
        self.bundle_id = self.metadata.get("bundle_id")

    def predict(self, features: Union[np.ndarray, pd.DataFrame, List[float], List[List[float]]]) -> np.ndarray:
        """
        Ejecuta la inferencia aplicando exactamente las transformaciones utilizadas al entrenar,
        independientemente del nombre de la familia (Mandato 4).
        Respeta la alineación por nombre de columnas cuando se recibe un DataFrame.
        """
        expected_features = self.metadata.get("feature_names", FEATURE_COLUMNS)

        if pd is not None and isinstance(features, pd.DataFrame):
            # Validar y alinear columnas del DataFrame con las esperadas
            if list(features.columns) == list(expected_features):
                X = np.asarray(features.values, dtype=np.float32)
            elif set(features.columns) == set(expected_features):
                # Columnas completas pero en orden distinto: reordenar exactamente
                X = np.asarray(features[expected_features].values, dtype=np.float32)
            else:
                missing = [c for c in expected_features if c not in features.columns]
                extra = [c for c in features.columns if c not in expected_features]
                raise ValueError(
                    f"Discrepancia en columnas del DataFrame de entrada. "
                    f"Faltantes: {missing}, Inesperadas: {extra}"
                )
        else:
            X = np.asarray(features, dtype=np.float32)
            if X.ndim == 1:
                X = X.reshape(1, -1)
            if X.shape[1] != len(expected_features):
                raise ValueError(
                    f"Dimensión incorrecta: se esperaban {len(expected_features)} características "
                    f"({expected_features}), se recibieron {X.shape[1]}"
                )

        # Validación estricta de valores finitos en entradas de inferencia
        if np.isnan(X).any() or np.isinf(X).any():
            raise ValueError("Las características de entrada para inferencia contienen valores no finitos (NaN o Inf).")

        # Aplicar escalado de entrada de forma consistente si el transformador está presente
        if self.scaler_x is not None:
            X_in = self.scaler_x.transform(X)
        else:
            X_in = X

        if self.model_type in ["dnn", "autoencoder_mlp"]:
            preds_raw = self.model.predict(X_in, verbose=0)
        else:
            preds_raw = self.model.predict(X_in)

        # Invertir escalado de salidas si fue ajustado
        if self.scaler_y is not None:
            preds_orig = self.scaler_y.inverse_transform(preds_raw)
        else:
            scale = np.array(self.metadata.get("target_scaler_scale", []), dtype=np.float32)
            mean = np.array(self.metadata.get("target_scaler_mean", []), dtype=np.float32)
            if len(scale) == preds_raw.shape[1] and len(mean) == preds_raw.shape[1]:
                preds_orig = preds_raw * scale + mean
            else:
                preds_orig = preds_raw

        return np.asarray(preds_orig, dtype=np.float32)


def export_bundle(
    predictor: UniversalSurrogatePredictor,
    export_dir: Union[str, Path],
    metadata_overlay: Optional[Dict[str, Any]] = None,
    strict_scientific: bool = False,
) -> Dict[str, Any]:
    """
    Exporta un bundle íntegro con modelo, transformadores y metadatos rigurosos.
    Aplica publicación atómica y recuperable:
      1. Escribe en directorio temporal aislado.
      2. Guarda transformadores y modelo.
      3. Calcula hashes criptográficos deterministas SHA-256.
      4. Deriva bundle_id a partir del contenido para asegurar identidad única.
      5. Ejecuta inferencia de prueba de autovalidación sobre el artefacto temporal.
      6. Publicación protegida: si el destino existe, crea backup previo. Si la sustitución
         falla, restaura de inmediato la versión anterior operativa.
      7. Emite puntero active_bundle.json para detección inmediata en watchers.
    """
    final_out_dir = Path(export_dir).resolve()
    final_out_dir.mkdir(parents=True, exist_ok=True)

    # Crear directorio temporal para escritura atómica (staging en el mismo sistema de archivos)
    temp_dir = Path(tempfile.mkdtemp(prefix=".staging_", dir=str(final_out_dir)))

    try:
        model_type = predictor.model_type
        metadata = dict(predictor.metadata)
        if metadata_overlay:
            metadata.update(metadata_overlay)

        if "strict_scientific" in metadata:
            strict_scientific = bool(metadata["strict_scientific"])

        is_test_bundle = bool(metadata.get("test_only") or metadata.get("is_test_bundle"))
        allow_default_bounds = bool(metadata.get("allow_default_bounds", False))

        # Validación estricta de rangos observados (Auditoría 04, Bloque 4)
        observed_ranges = metadata.get("observed_training_ranges") or metadata.get("observed_ranges")
        if observed_ranges is None:
            if strict_scientific:
                raise ValueError(
                    "Exportación científica rechazada: 'observed_training_ranges' es obligatorio "
                    "y debe provenir del entrenamiento registrado. No se permite sustitución automática por límites físicos."
                )
            else:
                observed_ranges = {k: list(v) for k, v in PHYSICAL_BOUNDS.items()}

        if not isinstance(observed_ranges, dict):
            raise ValueError("Formato inválido de 'observed_training_ranges': se esperaba un diccionario.")

        missing_feats = [col for col in FEATURE_COLUMNS if col not in observed_ranges]
        if missing_feats:
            raise ValueError(f"Rangos observados incompletos: faltan características requeridas: {missing_feats}")

        for col in FEATURE_COLUMNS:
            rng = observed_ranges[col]
            if not isinstance(rng, (list, tuple)) or len(rng) != 2:
                raise ValueError(f"Rango inválido para característica '{col}': se esperaba [min, max], recibido {rng}")
            min_v, max_v = rng[0], rng[1]
            if not isinstance(min_v, (int, float, np.number)) or not isinstance(max_v, (int, float, np.number)):
                raise ValueError(f"Límites no numéricos para característica '{col}': {rng}")
            if not np.isfinite(min_v) or not np.isfinite(max_v):
                raise ValueError(f"Límites no finitos para característica '{col}': {rng}")
            if min_v > max_v:
                raise ValueError(f"Orden inválido en límites de '{col}': min ({min_v}) > max ({max_v})")
            phys_min, phys_max = PHYSICAL_BOUNDS[col]
            if strict_scientific:
                if min_v < phys_min - 1e-4 or max_v > phys_max + 1e-4:
                    raise ValueError(
                        f"Rango observado para '{col}' ({rng}) excede los límites biofísicos permitidos [{phys_min}, {phys_max}]."
                    )
            else:
                if min_v > phys_max or max_v < phys_min:
                    raise ValueError(
                        f"Rango observado para '{col}' ({rng}) es incompatible con los límites biofísicos [{phys_min}, {phys_max}]."
                    )

        metadata["observed_training_ranges"] = observed_ranges
        metadata["schema_version"] = metadata.get("schema_version") or "2.0_revision_metodologica"
        metadata["model_type"] = model_type
        metadata["feature_names"] = list(FEATURE_COLUMNS)
        metadata["target_names"] = list(TARGET_COLUMNS)
        metadata["physical_bounds"] = {k: list(v) for k, v in PHYSICAL_BOUNDS.items()}
        metadata["feature_bounds"] = metadata["physical_bounds"]

        # Contrato explícito de preprocesamiento
        metadata["preprocessing_contract"] = {
            "scaler_x_applied": predictor.scaler_x is not None,
            "scaler_y_applied": predictor.scaler_y is not None,
            "inverse_transform_required": predictor.scaler_y is not None,
        }

        if predictor.scaler_y is not None:
            metadata["target_scaler_mean"] = predictor.scaler_y.mean_.tolist()
            metadata["target_scaler_scale"] = predictor.scaler_y.scale_.tolist()

        # Guardar escaladores obligatorios
        scalers_path = temp_dir / "scalers.pkl"
        with open(scalers_path, "wb") as f:
            pickle.dump({"scaler_x": predictor.scaler_x, "scaler_y": predictor.scaler_y}, f)

        # Guardar modelo según familia
        if model_type in ["dnn", "autoencoder_mlp"]:
            model_filename = "modelo_optimizado.h5"
            model_path = temp_dir / model_filename
            predictor.model.save(str(model_path))
        else:
            model_filename = f"model_{model_type}.pkl"
            model_path = temp_dir / model_filename
            with open(model_path, "wb") as f:
                pickle.dump(predictor.model, f)

        metadata["model_filename"] = model_filename

        # Calcular hashes SHA-256 de archivos del bundle para verificación de integridad
        file_hashes = {
            "scalers.pkl": compute_file_sha256(scalers_path),
            model_filename: compute_file_sha256(model_path),
        }
        metadata["file_hashes"] = file_hashes

        # Identificador canónico derivado de artefactos y metadatos que afectan al comportamiento (Auditoría 04, Bloque 4)
        canonical_identity_dict = {
            "model_type": model_type,
            "model_hash": file_hashes[model_filename],
            "scalers_hash": file_hashes.get("scalers.pkl", ""),
            "preprocessing_contract": metadata.get("preprocessing_contract", {}),
            "observed_training_ranges": {k: [float(observed_ranges[k][0]), float(observed_ranges[k][1])] for k in sorted(observed_ranges.keys())},
            "test_only": is_test_bundle,
        }
        canonical_identity_str = json.dumps(canonical_identity_dict, sort_keys=True, separators=(",", ":"))
        bundle_id = f"bundle_{model_type}_{hashlib.sha256(canonical_identity_str.encode('utf-8')).hexdigest()[:12]}"
        metadata["bundle_id"] = bundle_id
        predictor.bundle_id = bundle_id

        metadata_path = temp_dir / "bundle_metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

        # Archivo modelo_optimizado_metadata.json para compatibilidad directa
        compat_meta_path = temp_dir / "modelo_optimizado_metadata.json"
        compat_meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

        # Generar SHA256SUMS.txt local del bundle
        bundle_sums_lines = [
            f"{file_hashes['scalers.pkl']}  scalers.pkl",
            f"{file_hashes[model_filename]}  {model_filename}",
            f"{compute_file_sha256(metadata_path)}  bundle_metadata.json",
            f"{compute_file_sha256(compat_meta_path)}  modelo_optimizado_metadata.json",
        ]
        (temp_dir / "SHA256SUMS.txt").write_text("\n".join(bundle_sums_lines) + "\n", encoding="utf-8")

        # Autovalidación: Recargar bundle desde temporal y verificar equivalencia numérica
        is_test_bundle = bool(metadata.get("test_only") or metadata.get("is_test_bundle"))
        reloaded_predictor = load_bundle(temp_dir, allow_test_bundle=is_test_bundle)
        dummy_x = np.array([[50.0, 20.0, 8.0, 25.0, 70.0, 23.5, 1050.0, 0.65]], dtype=np.float32)
        pred_orig = predictor.predict(dummy_x)
        pred_reloaded = reloaded_predictor.predict(dummy_x)

        tol = 1e-4 if model_type not in ["dnn", "autoencoder_mlp"] else 1e-2
        max_diff = float(np.max(np.abs(pred_orig - pred_reloaded)))
        if np.isnan(max_diff) or max_diff > tol:
            raise RuntimeError(f"Error de serialización en bundle: discrepancia numérica de {max_diff} > {tol}")

        # Publicación atómica protegida con directorio versionado y puntero activo (Bloque 3)
        versioned_dir_name = bundle_id
        final_bundle_dir = final_out_dir / versioned_dir_name

        active_info = {
            "bundle_id": bundle_id,
            "bundle_dir": versioned_dir_name,
            "model_type": model_type,
            "model_filename": model_filename,
            "published_at_utc": time.time(),
            "test_only": is_test_bundle,
        }
        active_bytes = json.dumps(active_info, indent=2, ensure_ascii=False).encode("utf-8")
        (temp_dir / "active_bundle.json").write_bytes(active_bytes)

        # Mover directorio de staging a directorio versionado final
        backup_vdir = None
        if final_bundle_dir.exists():
            backup_vdir = final_out_dir / f".bak_{versioned_dir_name}_{time.time_ns()}"
            final_bundle_dir.rename(backup_vdir)

        try:
            temp_dir.rename(final_bundle_dir)
            if backup_vdir and backup_vdir.exists():
                shutil.rmtree(backup_vdir, ignore_errors=True)
        except Exception as move_err:
            if backup_vdir and backup_vdir.exists():
                if final_bundle_dir.exists():
                    shutil.rmtree(final_bundle_dir, ignore_errors=True)
                backup_vdir.rename(final_bundle_dir)
            raise RuntimeError(f"Fallo durante la publicación del directorio de bundle: {move_err}") from move_err

        # Conmutación atómica del puntero activo mediante archivo temporal y os.replace
        active_tmp = final_out_dir / f".active_{time.time_ns()}.tmp"
        active_tmp.write_bytes(active_bytes)
        os.replace(str(active_tmp), str(final_out_dir / "active_bundle.json"))

        try:
            if final_out_dir.parent.is_dir():
                (final_out_dir.parent / "active_bundle.json").write_bytes(active_bytes)
        except Exception:
            pass

        # Compatibilidad con accesos directos legacy en el directorio raíz mediante enlaces simbólicos atómicos
        legacy_files = [
            "scalers.pkl",
            model_filename,
            "bundle_metadata.json",
            "modelo_optimizado_metadata.json",
            "SHA256SUMS.txt",
        ]
        for fname in legacy_files:
            target_f = final_bundle_dir / fname
            link_f = final_out_dir / fname
            if target_f.is_file():
                try:
                    if link_f.is_symlink() or (link_f.is_file() and not link_f.is_symlink()):
                        link_f.unlink()
                    os.symlink(str(target_f.relative_to(final_out_dir)), str(link_f))
                except (OSError, NotImplementedError, ValueError):
                    pass

        final_model_path = final_bundle_dir / model_filename
        final_metadata_path = final_bundle_dir / "bundle_metadata.json"

        return {
            "export_dir": str(final_bundle_dir),
            "volume_dir": str(final_out_dir),
            "bundle_id": bundle_id,
            "model_file": str(final_model_path),
            "metadata_file": str(final_metadata_path),
            "model_type": model_type,
            "verification_diff": max_diff,
            "file_hashes": file_hashes,
            "status": "verified",
        }

    except ValueError:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except Exception as e:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"Fallo en la exportación atómica del bundle: {e}") from e


def load_bundle(
    bundle_dir: Union[str, Path],
    allow_test_bundle: bool = False,
    strict_scientific: bool = True,
) -> UniversalSurrogatePredictor:
    """
    Carga y valida exhaustivamente un bundle científico serializado desde un directorio local.
    Centraliza la validación para scientific_core y ModelStore (Bloque 2).
    Aplica las verificaciones obligatorias:
      - Existencia de directorio y metadatos.
      - Validación de esquema 'schema_version'.
      - Validación de familia de modelo.
      - Validación estricta de orden y nombres de entradas (feature_names) y salidas (target_names).
      - Verificación de metadatos científicos obligatorios ('observed_training_ranges').
      - Control de bundles 'test_only' fuera de modo de prueba.
      - Presencia y validez de 'file_hashes' y 'model_filename' declarado.
      - Comprobación criptográfica SHA-256 de cada archivo antes de deserializar.
      - Presencia obligatoria de 'scalers.pkl' y verificación de que scaler_x no sea None ni desajustado.
      - Prueba de inferencia controlada verificando forma y finitud de las salidas.
    """
    b_dir = Path(bundle_dir).resolve()
    if not b_dir.is_dir():
        raise FileNotFoundError(f"Directorio de bundle no encontrado: {bundle_dir}")

    # Si se pasa un directorio contenedor que posee active_bundle.json con puntero de versión
    active_ptr = b_dir / "active_bundle.json"
    if active_ptr.is_file():
        # Si scalers.pkl fue explícitamente eliminado en b_dir, no rescatar desde el subdirectorio
        # para garantizar fallo estricto sin operación degradada (test_bundle_hardening)
        scalers_root = b_dir / "scalers.pkl"
        if not scalers_root.exists() and (b_dir / "bundle_metadata.json").exists():
            raise FileNotFoundError(f"Archivo de escaladores no encontrado: scalers.pkl en {b_dir}")

        meta_local = b_dir / "bundle_metadata.json"
        is_direct_bundle = meta_local.is_file() and not meta_local.is_symlink()
        if not is_direct_bundle:
            try:
                active_info = json.loads(active_ptr.read_text(encoding="utf-8"))
                rel_dir = active_info.get("bundle_dir")
                if rel_dir and (b_dir / rel_dir).is_dir():
                    target_version_dir = (b_dir / rel_dir).resolve()
                    if (target_version_dir / "bundle_metadata.json").is_file():
                        b_dir = target_version_dir
            except Exception:
                pass

    meta_path = b_dir / "bundle_metadata.json"
    if not meta_path.is_file():
        meta_path = b_dir / "modelo_optimizado_metadata.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"Archivo de metadatos no encontrado en: {bundle_dir}")

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    # Comprobar presencia de archivo de modelo si está declarado antes de validaciones secundarias
    model_filename = metadata.get("model_filename")
    if model_filename and not (b_dir / model_filename).is_file():
        raise FileNotFoundError(f"Archivo declarado en bundle ausente en disco: '{model_filename}' en {b_dir}")

    # 1. Validación de esquema soportado (Auditoría 04, Bloque 4)
    supported_schemas = {"2.0", "2.0_revision_metodologica"}
    schema_ver = metadata.get("schema_version")
    if not schema_ver or str(schema_ver).strip() not in supported_schemas:
        raise ValueError(
            f"Versión de esquema (schema_version) no soportada o ausente: '{schema_ver}'. "
            f"Versiones soportadas: {sorted(supported_schemas)}"
        )

    # 2. Validación de familia de modelo
    model_type = metadata.get("model_type")
    valid_families = ["ridge", "random_forest", "xgboost", "dnn", "autoencoder_mlp"]
    if model_type not in valid_families:
        raise ValueError(
            f"Familia de modelo inválida o no reconocida: '{model_type}'. "
            f"Familias válidas: {valid_families}"
        )

    # 3. Validación estricta de nombres y orden de entradas y salidas
    meta_features = metadata.get("feature_names")
    if not meta_features or list(meta_features) != list(FEATURE_COLUMNS):
        raise ValueError(
            f"Contrato de características inválido en bundle: se esperaba orden exacto "
            f"{list(FEATURE_COLUMNS)}, pero el bundle declara {meta_features}"
        )

    meta_targets = metadata.get("target_names")
    if not meta_targets or list(meta_targets) != list(TARGET_COLUMNS):
        raise ValueError(
            f"Contrato de objetivos inválido en bundle: se esperaba orden exacto "
            f"{list(TARGET_COLUMNS)}, pero el bundle declara {meta_targets}"
        )

    # 4. Verificación de metadatos científicos obligatorios
    observed_ranges = metadata.get("observed_training_ranges") or metadata.get("observed_ranges")
    if not observed_ranges or not isinstance(observed_ranges, dict):
        if strict_scientific and not allow_test_bundle:
            raise ValueError(
                "Metadatos científicos requeridos ausentes: 'observed_training_ranges' no encontrado en el bundle."
            )
        else:
            observed_ranges = {k: list(v) for k, v in PHYSICAL_BOUNDS.items()}
            metadata["observed_training_ranges"] = observed_ranges
    else:
        missing_feats = [c for c in FEATURE_COLUMNS if c not in observed_ranges]
        if missing_feats:
            raise ValueError(f"Rangos observados incompletos en bundle: faltan características {missing_feats}")
        for c in FEATURE_COLUMNS:
            rng = observed_ranges[c]
            if not isinstance(rng, (list, tuple)) or len(rng) != 2:
                raise ValueError(f"Rango inválido para '{c}' en bundle: {rng}")
            if not np.isfinite(rng[0]) or not np.isfinite(rng[1]):
                raise ValueError(f"Límites no finitos para '{c}' en bundle: {rng}")
            if rng[0] > rng[1]:
                raise ValueError(f"Límites invertidos para '{c}' en bundle: {rng[0]} > {rng[1]}")

    # 5. Control de bundles test_only
    is_test_bundle = bool(metadata.get("test_only") or metadata.get("is_test_bundle"))
    if is_test_bundle and not allow_test_bundle:
        raise ValueError(
            "El bundle está marcado explícitamente como 'test_only' / 'is_test_bundle'. "
            "Rechazado en modo científico estricto fuera de pruebas."
        )

    # 6. Verificación de hashes obligatorios y archivos declarados antes de deserializar
    file_hashes = metadata.get("file_hashes")
    if not file_hashes or not isinstance(file_hashes, dict):
        raise ValueError("Hashes ausentes en metadatos del bundle ('file_hashes' no declarado o vacío).")

    model_filename = metadata.get("model_filename")
    if not model_filename:
        raise ValueError("Archivo de modelo no declarado en metadatos ('model_filename' ausente).")

    # Exigir explícitamente hash del modelo antes de deserializar (Auditoría 04, Bloque 4)
    if model_filename not in file_hashes:
        raise ValueError(
            f"Hash obligatorio del archivo de modelo '{model_filename}' ausente en 'file_hashes'."
        )

    prep_contract = metadata.get("preprocessing_contract", {})
    scaler_x_applied = bool(prep_contract.get("scaler_x_applied", True))
    scaler_y_applied = bool(prep_contract.get("scaler_y_applied", True))

    # Exigir hash de scalers.pkl cuando los transformadores hayan sido aplicados
    if (scaler_x_applied or scaler_y_applied) and "scalers.pkl" not in file_hashes:
        raise ValueError(
            "Hash obligatorio de 'scalers.pkl' ausente en 'file_hashes'."
        )

    # Validar existencia física y hashes SHA-256 de TODOS los archivos declarados antes de cargar
    for fname, expected_hash in file_hashes.items():
        fpath = b_dir / fname
        if not fpath.is_file():
            raise FileNotFoundError(f"Archivo declarado en bundle ausente en disco: '{fname}' en {b_dir}")
        actual_hash = compute_file_sha256(fpath)
        if actual_hash != expected_hash:
            raise ValueError(
                f"Fallo de integridad criptográfica en bundle: el hash de '{fname}' "
                f"({actual_hash}) no coincide con el registrado ({expected_hash})."
            )

    # 7. Carga y validación de escaladores
    prep_contract = metadata.get("preprocessing_contract", {})
    scaler_x_applied = bool(prep_contract.get("scaler_x_applied", True))
    scaler_y_applied = bool(prep_contract.get("scaler_y_applied", True))

    scalers_path = b_dir / "scalers.pkl"
    scaler_x = None
    scaler_y = None

    if scaler_x_applied:
        if not scalers_path.is_file():
            raise FileNotFoundError(
                f"Componente obligatorio 'scalers.pkl' no encontrado en {bundle_dir}. "
                f"El contrato indica que scaler_x fue aplicado."
            )
        with open(scalers_path, "rb") as f:
            scalers_dict = pickle.load(f)
        scaler_x = scalers_dict.get("scaler_x")
        scaler_y = scalers_dict.get("scaler_y")

        if scaler_x is None:
            raise ValueError(
                "Escalador requerido 'scaler_x' ausente o almacenado como None en scalers.pkl."
            )
        if not hasattr(scaler_x, "mean_") or len(scaler_x.mean_) != len(FEATURE_COLUMNS):
            raise ValueError(
                f"scaler_x no está debidamente ajustado o sus dimensiones no coinciden con las {len(FEATURE_COLUMNS)} características."
            )

        if scaler_y_applied:
            if scaler_y is None and "target_scaler_mean" in metadata and "target_scaler_scale" in metadata:
                s_y = StandardScaler()
                s_y.mean_ = np.array(metadata["target_scaler_mean"], dtype=np.float32)
                s_y.scale_ = np.array(metadata["target_scaler_scale"], dtype=np.float32)
                s_y.var_ = s_y.scale_ ** 2
                scaler_y = s_y
            if scaler_y is None or not hasattr(scaler_y, "mean_") or len(scaler_y.mean_) != len(TARGET_COLUMNS):
                raise ValueError("scaler_y requerido ausente, nulo o con dimensiones incoherentes con los 3 objetivos.")

    # 8. Carga del modelo (únicamente tras validar todos los hashes)
    model_path = b_dir / model_filename
    if str(model_filename).endswith(".h5"):
        if tf is None:
            raise RuntimeError("TensorFlow no disponible para cargar modelo .h5")
        model = tf.keras.models.load_model(str(model_path), compile=False)
    else:
        with open(model_path, "rb") as f:
            model = pickle.load(f)

    predictor = UniversalSurrogatePredictor(
        model=model,
        model_type=model_type,
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata=metadata,
    )
    predictor.bundle_id = metadata.get("bundle_id", f"bundle_{model_type}")

    # 9. Comprobación de forma y finitud de predicciones de prueba
    test_input = np.ones((2, len(FEATURE_COLUMNS)), dtype=np.float32) * 50.0
    try:
        test_preds = predictor.predict(test_input)
    except Exception as p_err:
        raise ValueError(f"Fallo al ejecutar predicción de prueba en el modelo cargado: {p_err}") from p_err

    if test_preds.shape != (2, len(TARGET_COLUMNS)):
        raise ValueError(
            f"Salida del modelo tiene dimensión {test_preds.shape}, "
            f"se requerían (2, {len(TARGET_COLUMNS)})."
        )
    if np.isnan(test_preds).any() or np.isinf(test_preds).any():
        raise ValueError("Las predicciones de prueba del modelo contienen valores no finitos (NaN o Inf).")

    return predictor
