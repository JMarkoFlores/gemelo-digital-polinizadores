from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_pipeline import FEATURE_COLUMNS, TARGET_COLUMNS, generate_synthetic_dataset, summarize_dataset
from pollinator_abm import ABMScenario, run_example_simulation
from training import export_model_bundle, train_surrogate_model

MODEL_DIR = Path("/modelos_ia")

st.set_page_config(
    page_title="Gemelos Digitales Lab",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS mínimo: solo tipografía y un divider decorativo ─────────────────────
# NO tocamos .stApp ni fondos globales — el tema del config.toml lo maneja.
st.markdown(
    """
    <style>
    h1 { font-size: 2rem; font-weight: 700; margin-bottom: 0.25rem; }
    .hero-badge {
        display: inline-block;
        background: #22c55e22;
        color: #22c55e;
        border: 1px solid #22c55e44;
        border-radius: 999px;
        padding: 0.15rem 0.75rem;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.6rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state() -> None:
    st.session_state.setdefault("dataset", None)
    st.session_state.setdefault("training_result", None)
    st.session_state.setdefault("export_result", None)
    st.session_state.setdefault("abm_preview", None)


def render_header() -> None:
    st.markdown('<span class="hero-badge">🌿 Agroecología</span>', unsafe_allow_html=True)
    st.title("Gemelos Digitales Lab")
    st.caption(
        "Entorno científico para construir datasets de paisaje agrícola, simular dinámicas "
        "de polinizadores y entrenar el surrogate que alimentará el backend de optimización."
    )
    st.divider()

    dataset_rows = len(st.session_state.dataset) if isinstance(st.session_state.dataset, pd.DataFrame) else 0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros listos", dataset_rows)
    col2.metric("Simulador ABM", "Mesa + grilla", "Activo")
    col3.metric("Surrogate", "Listo para entrenar")
    col4.metric("Volumen IA", "Disponible" if MODEL_DIR.exists() else "No montado")
    st.divider()


# ────────────────────────────────────────────────────────────────────────────
# TAB 1 — Dataset
# ────────────────────────────────────────────────────────────────────────────
def render_dataset_tab() -> None:
    controls_col, preview_col = st.columns([1, 1], gap="large")

    with controls_col:
        with st.container(border=True):
            st.markdown("#### 📂 Fuente de datos")
            source = st.radio(
                "Ruta de entrada",
                ["Generar dataset sintético", "Cargar CSV propio"],
                label_visibility="visible",
            )
            enrich_with_abm = st.toggle("Enriquecer con corridas ABM", value=True)
            st.markdown("---")

            if source == "Generar dataset sintético":
                c1, c2 = st.columns(2)
                sample_size = c1.slider("Número de registros", 120, 1200, 320, 20)
                random_state = c2.number_input("Semilla", min_value=1, max_value=9999, value=42, step=1)
                if st.button("▶ Generar dataset", use_container_width=True, type="primary"):
                    with st.spinner("Generando dataset sintético..."):
                        st.session_state.dataset = generate_synthetic_dataset(
                            n_samples=sample_size,
                            random_state=int(random_state),
                            enrich_with_abm=enrich_with_abm,
                        )
                        st.session_state.training_result = None
                        st.session_state.export_result = None
            else:
                uploaded_file = st.file_uploader("Arrastra o selecciona un CSV", type=["csv"])
                if uploaded_file is not None:
                    dataframe = pd.read_csv(uploaded_file)
                    missing = [c for c in FEATURE_COLUMNS + TARGET_COLUMNS if c not in dataframe.columns]
                    if missing:
                        st.error("El CSV debe incluir las columnas mínimas: " + ", ".join(FEATURE_COLUMNS + TARGET_COLUMNS))
                    else:
                        st.session_state.dataset = dataframe
                        st.session_state.training_result = None
                        st.session_state.export_result = None

        with st.container(border=True):
            st.info(
                "**Conectores reales listos:** GBIF (`pygbif`), ERA5 (`cdsapi`) y Earth Engine / "
                "Sentinel-2 (`earthengine-api`, `geemap`). Se activan cuando existan credenciales.",
                icon="ℹ️",
            )

    with preview_col:
        dataset = st.session_state.dataset
        if isinstance(dataset, pd.DataFrame):
            summary = summarize_dataset(dataset)
            with st.container(border=True):
                st.markdown("#### 📊 Resumen del dataset")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Filas", summary["rows"])
                m2.metric("Entradas", len(summary["input_features"]))
                m3.metric("Objetivos", len(summary["target_features"]))
                m4.metric("Nulos", summary["missing_values"])
            st.dataframe(dataset.head(12), use_container_width=True, hide_index=True)
            corr = dataset[FEATURE_COLUMNS + TARGET_COLUMNS].corr(numeric_only=True)
            fig = px.imshow(
                corr,
                aspect="auto",
                color_continuous_scale="Viridis",
                title="Correlaciones del dataset",
                template="plotly_dark",
            )
            fig.update_layout(height=400, margin=dict(l=0, r=0, t=48, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            with st.container(border=True):
                st.markdown("#### ⏳ Dataset pendiente")
                st.write("Genera o carga un dataset para habilitar el resto del flujo.")


# ────────────────────────────────────────────────────────────────────────────
# TAB 2 — ABM
# ────────────────────────────────────────────────────────────────────────────
def render_simulation_tab() -> None:
    left, right = st.columns([1, 1], gap="large")

    with left:
        with st.container(border=True):
            st.markdown("#### 🐝 Escenario de paisaje")
            crop_area        = st.slider("Área de cultivo (%)", 30, 85, 60)
            natural_area     = st.slider("Área seminatural (%)", 5, 45, 22)
            floral_strips    = st.slider("Franjas florales (%)", 0, 20, 8)
            pesticide        = st.slider("Nivel de pesticidas", 0, 100, 28)
            soil_management  = st.slider("Manejo del suelo", 20, 100, 70)
            temperature      = st.slider("Temperatura media (°C)", 16.0, 32.0, 24.0, 0.5)
            landscape_div    = st.slider("Diversidad del paisaje", 0.1, 1.0, 0.65, 0.05)
            steps            = st.slider("Pasos de simulación", 10, 60, 30)

            if st.button("▶ Ejecutar corrida ABM", use_container_width=True, type="primary"):
                with st.spinner("Simulando dinámica de polinizadores..."):
                    st.session_state.abm_preview = run_example_simulation(
                        ABMScenario(
                            crop_area_pct=float(crop_area),
                            natural_area_pct=float(natural_area),
                            floral_strips_pct=float(floral_strips),
                            pesticide_level=float(pesticide),
                            soil_management_score=float(soil_management),
                            temperature_c=float(temperature),
                            landscape_diversity=float(landscape_div),
                            steps=steps,
                            initial_pollinators=max(30, int(24 + natural_area * 1.2)),
                        )
                    )
            st.caption(
                "El ABM enriquece el dataset y aproxima abundancia/diversidad "
                "sin depender de datos externos desde el día uno."
            )

    with right:
        preview = st.session_state.abm_preview
        if preview:
            with st.container(border=True):
                st.markdown("#### 📈 Resultados de la corrida")
                c1, c2, c3 = st.columns(3)
                c1.metric("Población final",  int(preview["final_population"]))
                c2.metric("Población media",  f"{preview['mean_population']:.1f}")
                c3.metric("Diversidad",       f"{preview['diversity_index']:.1f}")

            habitat_map = pd.DataFrame(preview["resource_map"])
            heatmap = px.imshow(
                habitat_map,
                color_continuous_scale="YlGnBu",
                title="Mapa de recursos al final de la corrida",
                template="plotly_dark",
            )
            heatmap.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(heatmap, use_container_width=True)

            history_fig = go.Figure()
            history_fig.add_scatter(
                y=preview["population_history"], mode="lines+markers", name="Población",
                line=dict(color="#22c55e", width=2),
            )
            history_fig.update_layout(
                height=250,
                margin=dict(l=0, r=0, t=36, b=0),
                template="plotly_dark",
                title="Trayectoria poblacional",
                xaxis_title="Paso",
                yaxis_title="Número de agentes",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(history_fig, use_container_width=True)
        else:
            with st.container(border=True):
                st.markdown("#### ⏳ Previsualización pendiente")
                st.write(
                    "Ejecuta una corrida ABM para inspeccionar el paisaje, "
                    "los recursos y la respuesta de la población."
                )


# ────────────────────────────────────────────────────────────────────────────
# TAB 3 — Entrenamiento
# ────────────────────────────────────────────────────────────────────────────
def render_training_tab() -> None:
    dataset = st.session_state.dataset
    if not isinstance(dataset, pd.DataFrame):
        st.warning("⚠️  Primero genera o carga un dataset válido para habilitar el entrenamiento.")
        return

    left, right = st.columns([1, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("#### ⚙️ Hiperparámetros")
            epochs       = st.slider("Épocas", 10, 120, 35, 5)
            batch_size   = st.select_slider("Batch size", options=[8, 16, 24, 32, 48, 64], value=24)
            random_state = st.number_input("Semilla de entrenamiento", min_value=1, max_value=9999, value=42)
            st.markdown("---")
            st.markdown("**Entradas detectadas:**")
            st.code(", ".join(FEATURE_COLUMNS), language=None)
            st.markdown("**Objetivos detectados:**")
            st.code(", ".join(TARGET_COLUMNS), language=None)
            train_button = st.button("▶ Iniciar entrenamiento", type="primary", use_container_width=True)

    with right:
        progress_bar       = st.progress(0)
        status_placeholder = st.empty()
        chart_placeholder  = st.empty()

        if train_button:
            with st.spinner("Entrenando la red neuronal surrogate..."):
                st.session_state.training_result = train_surrogate_model(
                    dataframe=dataset,
                    progress_bar=progress_bar,
                    status_placeholder=status_placeholder,
                    chart_placeholder=chart_placeholder,
                    epochs=epochs,
                    batch_size=batch_size,
                    random_state=int(random_state),
                )
                status_placeholder.success("✅  Entrenamiento completado.")

        training_result = st.session_state.training_result
        if training_result:
            metrics = training_result["metrics"]
            metric_rows = [
                {"target": target, "MAE": round(v["mae"], 4), "RMSE": round(v["rmse"], 4), "R²": round(v["r2"], 4)}
                for target, v in metrics.items()
            ]
            with st.container(border=True):
                st.markdown("#### 📋 Métricas de evaluación")
                st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)
                st.caption(f"Tiempo total: {training_result['duration_seconds']:.2f} segundos")


# ────────────────────────────────────────────────────────────────────────────
# TAB 4 — Exportación
# ────────────────────────────────────────────────────────────────────────────
def render_export_tab() -> None:
    training_result = st.session_state.training_result
    if not training_result:
        st.info("ℹ️  Completa el entrenamiento para exportar `modelo_optimizado.h5` al volumen compartido.")
        return

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        with st.container(border=True):
            st.markdown("#### 💾 Destino del modelo")
            st.code(str(MODEL_DIR / "modelo_optimizado.h5"), language=None)
            if st.button("📤 Exportar modelo entrenado", use_container_width=True, type="primary"):
                st.session_state.export_result = export_model_bundle(
                    training_result["model"],
                    MODEL_DIR,
                    training_result["metrics"],
                    training_result["target_scaler_mean"],
                    training_result["target_scaler_scale"],
                )

    with col2:
        export_result = st.session_state.export_result
        if export_result:
            st.success("✅  Modelo exportado correctamente.")
            with st.container(border=True):
                st.json(export_result)
        else:
            existing_model = MODEL_DIR / "modelo_optimizado.h5"
            if existing_model.exists():
                with st.container(border=True):
                    st.info(f"Ya existe un modelo en el volumen: `{existing_model}`")
            else:
                with st.container(border=True):
                    st.markdown("#### ⏳ Sin exportaciones aún")
                    st.write("El modelo exportado aparecerá aquí una vez que completes la exportación.")


# ────────────────────────────────────────────────────────────────────────────
def main() -> None:
    initialize_state()
    render_header()
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📂 Datos y pipeline", "🐝 Simulador ABM", "🧠 Entrenamiento", "💾 Exportación"]
    )
    with tab1:
        render_dataset_tab()
    with tab2:
        render_simulation_tab()
    with tab3:
        render_training_tab()
    with tab4:
        render_export_tab()


if __name__ == "__main__":
    main()
