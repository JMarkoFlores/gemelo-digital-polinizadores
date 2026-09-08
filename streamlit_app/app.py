from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_pipeline import FEATURE_COLUMNS, TARGET_COLUMNS, generate_synthetic_dataset, summarize_dataset
from pollinator_abm import ABMScenario, run_example_simulation
from training import export_model_bundle, train_surrogate_model
from advanced_training import train_and_evaluate_all_models
from reports import generate_excel_report, generate_word_report, generate_pdf_report

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
import datetime

def render_training_tab() -> None:
    dataset = st.session_state.dataset
    if not isinstance(dataset, pd.DataFrame):
        st.warning("⚠️  Primero genera o carga un dataset válido para habilitar el entrenamiento.")
        return

    # Add custom style for the big red button and dark theme aesthetics
    st.markdown(
        """
        <style>
        div.stButton > button:first-child {
            background-color: #ff4b4b;
            color: white;
            border: none;
            padding: 0.75rem 1rem;
        }
        div.stButton > button:first-child:hover {
            background-color: #ff3333;
            color: white;
            border: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        - División temporal: ajuste con `Time Series Split` (K-Folds adaptado al dataset).
        - Modelos tabulares: ajuste con MultiOutputRegressor.
        - Modelos secuenciales: holdout temporal con validacion separada (Redes Neuronales).
        - Objetivo de seleccion: mejor `R2`, luego `MAE` y `RMSE`.
        """
    )
    
    if st.button("Entrenar y comparar modelos", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("Entrenando modelos... esto puede tardar un momento"):
            st.session_state.training_result = train_and_evaluate_all_models(
                dataframe=dataset,
                progress_bar=progress_bar,
                status_text=status_text
            )
            progress_bar.empty()
            status_text.empty()
            
    training_result = st.session_state.training_result
    if training_result:
        results_df = training_result["results_df"]
        best_overall = training_result["best_overall"]
        
        st.success(f"Entrenamiento completado. Mejor modelo: {best_overall}")
        
        # 1. Registro de modelos
        st.markdown("### Registro de modelos")
        registro_df = pd.DataFrame()
        registro_df["nombre"] = results_df["Modelo"]
        registro_df["version"] = "1.0.0"
        registro_df["r2_score"] = results_df["CV_R2_Mean"].round(4)
        registro_df["mae"] = results_df["CV_MAE_Mean"].round(4)
        registro_df["rmse"] = results_df["CV_RMSE_Mean"].round(4)
        registro_df["mape"] = results_df["CV_MAPE_Mean"].round(4)
        registro_df["expl_var"] = results_df["CV_ExplVar_Mean"].round(4)
        registro_df["activo"] = registro_df["nombre"] == best_overall
        registro_df["fecha_entrenamiento"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        st.dataframe(
            registro_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "activo": st.column_config.CheckboxColumn("activo")
            }
        )
        
        # 2. Tabla comparativa
        st.markdown("### Tabla comparativa")
        comparativa_df = pd.DataFrame()
        comparativa_df["Modelo"] = results_df["Modelo"]
        comparativa_df["R2 Score"] = results_df["CV_R2_Mean"].round(4)
        comparativa_df["Expl Variance"] = results_df["CV_ExplVar_Mean"].round(4)
        comparativa_df["MAE"] = results_df["CV_MAE_Mean"].round(4)
        comparativa_df["RMSE"] = results_df["CV_RMSE_Mean"].round(4)
        comparativa_df["MAPE"] = results_df["CV_MAPE_Mean"].round(4)
        comparativa_df["MaxError"] = results_df["CV_MaxError_Mean"].round(4)
        comparativa_df["MedAE"] = results_df["CV_MedAE_Mean"].round(4)
        comparativa_df["Train Seconds"] = results_df["Train_Time_Mean"].round(4)
        comparativa_df["Infer Seconds"] = results_df["Infer_Time_Mean"].round(4)
        
        st.dataframe(comparativa_df, use_container_width=True, hide_index=True)
        
        # 3. Comparacion de metricas clave
        st.markdown("### Comparacion de metricas clave")
        # Displaying R2 Score and Explained Variance as they are typically bounded 0-1
        plot_df = results_df[["Modelo", "CV_R2_Mean", "CV_ExplVar_Mean"]].copy()
        plot_df.rename(columns={"CV_R2_Mean": "R2 Score", "CV_ExplVar_Mean": "Expl Variance"}, inplace=True)
        plot_df = plot_df.melt(id_vars="Modelo", var_name="metrica", value_name="valor")
        
        fig_metrics = px.bar(
            plot_df, 
            x="Modelo", 
            y="valor", 
            color="metrica", 
            barmode="group",
            color_discrete_sequence=["#73b0ff", "#ffbaba"]
        )
        fig_metrics.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0), yaxis_title="")
        st.plotly_chart(fig_metrics, use_container_width=True)
        
        # 4. Modelo a inspeccionar
        st.markdown("### Modelo a inspeccionar")
        selected_model = st.selectbox("Seleccionar modelo:", options=results_df["Modelo"].tolist(), label_visibility="collapsed")
        
        sel_row = results_df[results_df["Modelo"] == selected_model].iloc[0]
        
        # Big metric numbers
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("R2 Score", f"{sel_row['CV_R2_Mean']:.4f}")
        m2.metric("MAE", f"{sel_row['CV_MAE_Mean']:.4f}")
        m3.metric("RMSE", f"{sel_row['CV_RMSE_Mean']:.4f}")
        m4.metric("MAPE", f"{sel_row['CV_MAPE_Mean']:.4f}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        c_chart1, c_chart2 = st.columns(2)
        
        last_y_true = sel_row["last_y_true"]
        last_y_pred = sel_row["last_y_pred"]
        
        if last_y_true is not None and last_y_pred is not None:
            with c_chart1:
                st.markdown("**Valores Predichos vs Reales (Primer Objetivo)**")
                fig_scatter = go.Figure()
                fig_scatter.add_scatter(
                    x=last_y_true[:, 0], 
                    y=last_y_pred[:, 0], 
                    mode="markers", 
                    marker=dict(color="#73b0ff", opacity=0.7)
                )
                min_val = min(last_y_true[:, 0].min(), last_y_pred[:, 0].min())
                max_val = max(last_y_true[:, 0].max(), last_y_pred[:, 0].max())
                fig_scatter.add_shape(type="line", x0=min_val, y0=min_val, x1=max_val, y1=max_val, line=dict(color="white", dash="dash"))
                fig_scatter.update_layout(template="plotly_dark", height=280, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Valores Reales", yaxis_title="Valores Predichos")
                st.plotly_chart(fig_scatter, use_container_width=True)
                
            with c_chart2:
                st.markdown("**Distribución de Residuos (Primer Objetivo)**")
                fig_res = go.Figure()
                residuals = last_y_true[:, 0] - last_y_pred[:, 0]
                fig_res.add_scatter(
                    x=last_y_pred[:, 0], 
                    y=residuals, 
                    mode="markers", 
                    marker=dict(color="#ffbaba", opacity=0.7)
                )
                fig_res.add_shape(type="line", x0=last_y_pred[:, 0].min(), y0=0, x1=last_y_pred[:, 0].max(), y1=0, line=dict(color="white", dash="dash"))
                fig_res.update_layout(template="plotly_dark", height=280, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Valores Predichos", yaxis_title="Error Residual")
                st.plotly_chart(fig_res, use_container_width=True)


# ────────────────────────────────────────────────────────────────────────────
# TAB 4 — Exportación
# ────────────────────────────────────────────────────────────────────────────
def render_export_tab() -> None:
    dataset = st.session_state.dataset
    training_result = st.session_state.training_result
    if not training_result:
        st.info("ℹ️  Completa el entrenamiento para exportar `modelo_optimizado.h5` al volumen compartido y generar reportes.")
        return

    results_df = training_result["results_df"]
    best_overall = training_result["best_overall"]
    best_keras_model = training_result["best_keras_model"]
    target_scaler = training_result["target_scaler"]
    dataset_summary = training_result["dataset_summary"]

    # Recrear tablas de la UI para los reportes
    registro_df = pd.DataFrame()
    registro_df["nombre"] = results_df["Modelo"]
    registro_df["version"] = "1.0.0"
    registro_df["r2_score"] = results_df["CV_R2_Mean"].round(4)
    registro_df["mae"] = results_df["CV_MAE_Mean"].round(4)
    registro_df["rmse"] = results_df["CV_RMSE_Mean"].round(4)
    registro_df["mape"] = results_df["CV_MAPE_Mean"].round(4)
    registro_df["expl_var"] = results_df["CV_ExplVar_Mean"].round(4)
    registro_df["activo"] = (registro_df["nombre"] == best_overall).map({True: "Sí", False: "No"})
    registro_df["fecha_entrenamiento"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    comparativa_df = pd.DataFrame()
    comparativa_df["Modelo"] = results_df["Modelo"]
    comparativa_df["R2 Score"] = results_df["CV_R2_Mean"].round(4)
    comparativa_df["Expl Variance"] = results_df["CV_ExplVar_Mean"].round(4)
    comparativa_df["MAE"] = results_df["CV_MAE_Mean"].round(4)
    comparativa_df["RMSE"] = results_df["CV_RMSE_Mean"].round(4)
    comparativa_df["MAPE"] = results_df["CV_MAPE_Mean"].round(4)
    comparativa_df["MaxError"] = results_df["CV_MaxError_Mean"].round(4)
    comparativa_df["MedAE"] = results_df["CV_MedAE_Mean"].round(4)
    comparativa_df["Train Seconds"] = results_df["Train_Time_Mean"].round(4)
    comparativa_df["Infer Seconds"] = results_df["Infer_Time_Mean"].round(4)

    dataset_info_df = pd.DataFrame([
        {"Propiedad": "Cantidad de Datos Entrenados (Filas)", "Detalle": str(len(dataset))},
        {"Propiedad": "Campos de Entrada (Features)", "Detalle": ", ".join(dataset.columns.intersection(FEATURE_COLUMNS))},
        {"Propiedad": "Campos Objetivo (Targets)", "Detalle": ", ".join(dataset.columns.intersection(TARGET_COLUMNS))}
    ])

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        with st.container(border=True):
            st.markdown("#### 📄 Generar Reportes")
            st.write("Descarga los resultados de la validación cruzada y los datos entrenados.")
            
            excel_bytes = generate_excel_report(registro_df, comparativa_df, dataset_info_df, dataset, best_overall)
            st.download_button("Descargar Excel", data=excel_bytes, file_name="reporte_modelos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            word_bytes = generate_word_report(registro_df, comparativa_df, dataset_info_df, best_overall)
            st.download_button("Descargar Word", data=word_bytes, file_name="reporte_modelos.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            
            pdf_bytes = generate_pdf_report(registro_df, comparativa_df, dataset_info_df, best_overall)
            st.download_button("Descargar PDF", data=pdf_bytes, file_name="reporte_modelos.pdf", mime="application/pdf", use_container_width=True)

    with col2:
        with st.container(border=True):
            st.markdown("#### 💾 Destino del modelo")
            st.code(str(MODEL_DIR / "modelo_optimizado.h5"), language=None)
            st.caption("Nota: El backend React requiere un archivo H5, por lo que se exportará la mejor Red Neuronal/Híbrida encontrada.")
            if st.button("📤 Exportar modelo entrenado", use_container_width=True, type="primary"):
                # Mocking a metrics dict for compatibility with existing export
                metrics = {"general": {"mae": results_df.iloc[0]["CV_MAE_Mean"], "rmse": 0, "r2": 0}}
                st.session_state.export_result = export_model_bundle(
                    best_keras_model,
                    MODEL_DIR,
                    metrics,
                    target_scaler.mean_.tolist(),
                    target_scaler.scale_.tolist(),
                )

        export_result = st.session_state.export_result
        if export_result:
            st.success("✅  Modelo Keras exportado correctamente.")
            with st.container(border=True):
                st.json(export_result)



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
