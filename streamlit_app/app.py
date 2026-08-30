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

st.set_page_config(page_title="Gemelos Digitales Lab", page_icon="🌿", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(34, 197, 94, 0.18), transparent 28%),
            linear-gradient(180deg, #f8fafc 0%, #eefbf4 52%, #f8fafc 100%);
    }
    .hero {
        padding: 1.75rem 1.9rem;
        border-radius: 28px;
        background: linear-gradient(135deg, #052e16, #14532d 52%, #1d4ed8 100%);
        color: white;
        box-shadow: 0 24px 60px rgba(5, 46, 22, 0.24);
        margin-bottom: 1rem;
    }
    .section-card {
        padding: 1rem 1.15rem;
        border-radius: 22px;
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(15, 23, 42, 0.08);
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
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
    st.markdown(
        """
        <div class="hero">
          <h1>Gemelos Digitales Lab</h1>
          <p>Entorno cientifico para construir datasets de paisaje agricola, simular dinamicas de polinizadores y entrenar el surrogate que alimentara el backend de optimizacion.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4 = st.columns(4)
    dataset_rows = len(st.session_state.dataset) if isinstance(st.session_state.dataset, pd.DataFrame) else 0
    col1.metric("Registros listos", dataset_rows)
    col2.metric("ABM", "Activo", "Mesa + grilla")
    col3.metric("Modelo surrogate", "Listo para entrenar")
    col4.metric("Volumen IA", "Disponible" if MODEL_DIR.exists() else "No montado")


def render_dataset_tab() -> None:
    st.subheader("1. Datos base y pipeline")
    controls_col, preview_col = st.columns([0.95, 1.05])

    with controls_col:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("#### Fuente de datos")
        source = st.radio(
            "Selecciona una ruta de entrada",
            ["Generar dataset sintetico", "Cargar CSV propio"],
            label_visibility="collapsed",
        )
        enrich_with_abm = st.toggle("Enriquecer el dataset con corridas ABM", value=True)

        if source == "Generar dataset sintetico":
            c1, c2 = st.columns(2)
            sample_size = c1.slider("Numero de registros", 120, 1200, 320, 20)
            random_state = c2.number_input("Semilla", min_value=1, max_value=9999, value=42, step=1)
            if st.button("Generar dataset", use_container_width=True):
                with st.spinner("Generando dataset sintetico..."):
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
                missing = [column for column in FEATURE_COLUMNS + TARGET_COLUMNS if column not in dataframe.columns]
                if missing:
                    st.error(
                        "El CSV debe incluir las columnas minimas: " + ", ".join(FEATURE_COLUMNS + TARGET_COLUMNS)
                    )
                else:
                    st.session_state.dataset = dataframe
                    st.session_state.training_result = None
                    st.session_state.export_result = None

        st.info(
            "Conectores reales preparados: GBIF (`pygbif`), ERA5 (`cdsapi`) y Earth Engine / Sentinel-2 (`earthengine-api`, `geemap`). Se activan cuando existan credenciales y dependencias."
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with preview_col:
        dataset = st.session_state.dataset
        if isinstance(dataset, pd.DataFrame):
            summary = summarize_dataset(dataset)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Filas", summary["rows"])
            m2.metric("Entradas", len(summary["input_features"]))
            m3.metric("Objetivos", len(summary["target_features"]))
            m4.metric("Nulos", summary["missing_values"])
            st.dataframe(dataset.head(12), use_container_width=True, hide_index=True)
            corr = dataset[FEATURE_COLUMNS + TARGET_COLUMNS].corr(numeric_only=True)
            fig = px.imshow(corr, aspect="auto", color_continuous_scale="Viridis", title="Correlaciones del dataset")
            fig.update_layout(height=430, margin=dict(l=0, r=0, t=48, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("#### Dataset pendiente")
            st.write("Genera o carga un dataset para habilitar el resto del flujo.")
            st.markdown("</div>", unsafe_allow_html=True)


def render_simulation_tab() -> None:
    st.subheader("2. Simulador ABM de polinizadores")
    left, right = st.columns([0.95, 1.05])
    with left:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("#### Escenario de paisaje")
        crop_area = st.slider("Area de cultivo (%)", 30, 85, 60)
        natural_area = st.slider("Area seminatural (%)", 5, 45, 22)
        floral_strips = st.slider("Franjas florales (%)", 0, 20, 8)
        pesticide = st.slider("Nivel de pesticidas", 0, 100, 28)
        soil_management = st.slider("Manejo del suelo", 20, 100, 70)
        temperature = st.slider("Temperatura media (C)", 16.0, 32.0, 24.0, 0.5)
        landscape_diversity = st.slider("Diversidad del paisaje", 0.1, 1.0, 0.65, 0.05)
        steps = st.slider("Pasos de simulacion", 10, 60, 30)

        if st.button("Ejecutar corrida ABM", use_container_width=True):
            with st.spinner("Simulando dinamica de polinizadores..."):
                st.session_state.abm_preview = run_example_simulation(
                    ABMScenario(
                        crop_area_pct=float(crop_area),
                        natural_area_pct=float(natural_area),
                        floral_strips_pct=float(floral_strips),
                        pesticide_level=float(pesticide),
                        soil_management_score=float(soil_management),
                        temperature_c=float(temperature),
                        landscape_diversity=float(landscape_diversity),
                        steps=steps,
                        initial_pollinators=max(30, int(24 + natural_area * 1.2)),
                    )
                )
        st.caption("El ABM se usa para enriquecer el dataset y aproximar abundancia/diversidad sin depender de datos externos desde el dia uno.")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        preview = st.session_state.abm_preview
        if preview:
            c1, c2, c3 = st.columns(3)
            c1.metric("Poblacion final", int(preview["final_population"]))
            c2.metric("Poblacion media", f"{preview['mean_population']:.1f}")
            c3.metric("Diversidad", f"{preview['diversity_index']:.1f}")

            habitat_map = pd.DataFrame(preview["resource_map"])
            heatmap = px.imshow(habitat_map, color_continuous_scale="YlGnBu", title="Mapa de recursos al final de la corrida")
            heatmap.update_layout(height=320, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(heatmap, use_container_width=True)

            history_fig = go.Figure()
            history_fig.add_scatter(y=preview["population_history"], mode="lines+markers", name="Poblacion")
            history_fig.update_layout(
                height=260,
                margin=dict(l=0, r=0, t=28, b=0),
                template="plotly_white",
                title="Trayectoria poblacional",
                xaxis_title="Paso",
                yaxis_title="Numero de agentes",
            )
            st.plotly_chart(history_fig, use_container_width=True)
        else:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("#### Previsualizacion pendiente")
            st.write("Ejecuta una corrida ABM para inspeccionar el paisaje, los recursos y la respuesta de la poblacion.")
            st.markdown("</div>", unsafe_allow_html=True)


def render_training_tab() -> None:
    st.subheader("3. Entrenamiento del surrogate")
    dataset = st.session_state.dataset
    if not isinstance(dataset, pd.DataFrame):
        st.warning("Primero genera o carga un dataset valido para habilitar el entrenamiento.")
        return

    left, right = st.columns([0.9, 1.1])
    with left:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        epochs = st.slider("Epocas", 10, 120, 35, 5)
        batch_size = st.select_slider("Batch size", options=[8, 16, 24, 32, 48, 64], value=24)
        random_state = st.number_input("Semilla de entrenamiento", min_value=1, max_value=9999, value=42)
        st.write("Entradas detectadas:")
        st.code(", ".join(FEATURE_COLUMNS))
        st.write("Objetivos detectados:")
        st.code(", ".join(TARGET_COLUMNS))
        train_button = st.button("Iniciar Entrenamiento", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        chart_placeholder = st.empty()

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
                status_placeholder.success("Entrenamiento completado.")

        training_result = st.session_state.training_result
        if training_result:
            metrics = training_result["metrics"]
            metric_rows = []
            for target, values in metrics.items():
                metric_rows.append(
                    {
                        "target": target,
                        "MAE": round(values["mae"], 4),
                        "RMSE": round(values["rmse"], 4),
                        "R2": round(values["r2"], 4),
                    }
                )
            st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)
            st.caption(f"Tiempo total: {training_result['duration_seconds']:.2f} segundos")


def render_export_tab() -> None:
    st.subheader("4. Exportacion del modelo")
    training_result = st.session_state.training_result
    if not training_result:
        st.info("Completa el entrenamiento para exportar `modelo_optimizado.h5` al volumen compartido.")
        return

    col1, col2 = st.columns([0.9, 1.1])
    with col1:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.write("Destino del modelo compartido")
        st.code(str(MODEL_DIR / "modelo_optimizado.h5"))
        if st.button("Exportar modelo entrenado", use_container_width=True):
            st.session_state.export_result = export_model_bundle(
                training_result["model"],
                MODEL_DIR,
                training_result["metrics"],
                training_result["target_scaler_mean"],
                training_result["target_scaler_scale"],
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        export_result = st.session_state.export_result
        if export_result:
            st.success("Modelo exportado correctamente.")
            st.json(export_result)
        else:
            existing_model = MODEL_DIR / "modelo_optimizado.h5"
            if existing_model.exists():
                st.info(f"Ya existe un modelo en el volumen: {existing_model}")


def main() -> None:
    initialize_state()
    render_header()
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Datos y pipeline",
            "Simulador ABM",
            "Entrenamiento",
            "Exportacion",
        ]
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
