import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from scipy import stats

def cohen_d(x, y):
    # x: compare model error, y: best model error
    # If best model has smaller error, x - y is positive. Positive d means best model is better.
    diff = x - y
    std_diff = np.std(diff, ddof=1)
    if std_diff == 0:
        return 0.0
    return np.mean(diff) / std_diff

def render_robust_tests_tab() -> None:
    training_result = st.session_state.get("training_result")
    if not training_result:
        st.info("ℹ️ Completa el entrenamiento primero para poder realizar las pruebas estadísticas robustas.")
        return

    results_df = training_result["results_df"]
    best_model_name = training_result["best_overall"]
    
    st.markdown("### Validación con Pruebas Estadísticas Robustas")
    st.write(
        f"Para validar estadísticamente el rendimiento, se utiliza el modelo ganador (**{best_model_name}**) "
        "como 'Modelo Propuesto' (baseline de comparación). A continuación, se aplican pruebas estadísticas "
        "a los errores absolutos (out-of-fold) de cada modelo:"
    )
    
    st.markdown("""
    1. **Shapiro-Wilk (p-valor):** Evalúa la normalidad de los residuos.
    2. **T-Student Apareado (p-valor):** Compara los errores absolutos. Asume normalidad.
    3. **Wilcoxon Signed-Rank (p-valor):** Prueba no paramétrica.
    4. **D de Cohen:** Tamaño del efecto. Valores positivos indican que el baseline es superior.
    """)

    model_names = results_df["Modelo"].tolist()
    
    best_row = results_df[results_df["Modelo"] == best_model_name].iloc[0]
    best_y_true = best_row.get("last_y_true")
    best_y_pred = best_row.get("last_y_pred")
    
    if best_y_true is None or best_y_pred is None:
        st.warning("No hay datos de predicción detallados disponibles. Reentrena el modelo.")
        return

    best_abs_error = np.mean(np.abs(best_y_true - best_y_pred), axis=1)
    
    table_data = []
    all_abs_errors = []
    all_fold_maes = []
    
    # Bonferroni correction alpha
    alpha_base = 0.05
    comparisons = len(model_names) - 1
    alpha_bonf = alpha_base / comparisons if comparisons > 0 else alpha_base
    
    # For fallback fold calculation
    from sklearn.model_selection import TimeSeriesSplit
    kf_fallback = TimeSeriesSplit(n_splits=5)
    
    for model_name in model_names:
        row = results_df[results_df["Modelo"] == model_name].iloc[0]
        y_true = row["last_y_true"]
        y_pred = row["last_y_pred"]
        
        abs_error = np.mean(np.abs(y_true - y_pred), axis=1)
        residuals = np.mean(y_true - y_pred, axis=1)
        
        all_abs_errors.append(abs_error)
        
        if "fold_maes" in row:
            all_fold_maes.append(row["fold_maes"])
        else:
            # Fallback if the user hasn't retrained yet (assuming default 5)
            f_maes = []
            for train_idx, val_idx in kf_fallback.split(y_true):
                f_maes.append(np.mean(abs_error[val_idx]))
            all_fold_maes.append(f_maes)
            
        # 1. Shapiro-Wilk on residuals
        try:
            _, p_shapiro = stats.shapiro(residuals)
        except:
            p_shapiro = np.nan
            
        if model_name == best_model_name:
            p_t = np.nan
            p_w = np.nan
            d_effect = np.nan
            conclusion = "Modelo Baseline"
        else:
            # 2. T-Student
            try:
                _, p_t = stats.ttest_rel(abs_error, best_abs_error)
            except:
                p_t = np.nan
                
            # 3. Wilcoxon
            try:
                _, p_w = stats.wilcoxon(abs_error, best_abs_error)
            except:
                p_w = np.nan
                
            # 4. Cohen's D (Positive if abs_error > best_abs_error)
            d_effect = cohen_d(abs_error, best_abs_error)
            
            # Logic for conclusion
            active_p = p_t if p_shapiro > 0.05 else p_w
            test_used = "T-Student" if p_shapiro > 0.05 else "Wilcoxon"
            
            if active_p < alpha_bonf:
                conclusion = f"Baseline significativamente mejor ({test_used})" if d_effect > 0 else f"Modelo significativamente mejor ({test_used})"
            else:
                conclusion = f"Sin diferencia significativa ({test_used})"
            
        table_data.append({
            "Modelo de IA": model_name,
            "Shapiro-Wilk (p-valor)": p_shapiro,
            "T-Student Apareado (p-valor)": p_t,
            "Wilcoxon (p-valor)": p_w,
            "D de Cohen": d_effect,
            "Decisión (Bonferroni)": conclusion
        })
        
    df_tests = pd.DataFrame(table_data)
    
    format_dict = {
        "Shapiro-Wilk (p-valor)": "{:.4e}",
        "T-Student Apareado (p-valor)": "{:.4e}",
        "Wilcoxon (p-valor)": "{:.4e}",
        "D de Cohen": "{:.4f}"
    }
    
    st.markdown("##### 📋 Pruebas Estadísticas Pareadas (T7)")
    st.dataframe(df_tests.style.format(format_dict, na_rep="- (Ref)"), use_container_width=True)
    
    nota_metodologica = "Nota metodológica: estas pruebas asumen independencia entre observaciones; al proceder de validación cruzada, dicha independencia es parcial, lo que puede subestimar la varianza real de los errores (Dietterich, 1998; Nadeau & Bengio, 2003). Los resultados deben interpretarse como una referencia complementaria al Test de Friedman/Nemenyi, que sí opera correctamente a nivel de fold."
    st.caption(f"*{nota_metodologica}*")
    st.session_state["nota_metodologica_b1"] = nota_metodologica
    
    # Interpretación y Explicabilidad (Análisis sobre T7)
    interpretations_b1 = []
    significant_against_baseline = []
    for row in table_data:
        m = row["Modelo de IA"]
        if m == best_model_name:
            continue
            
        active_p = row["T-Student Apareado (p-valor)"] if row["Shapiro-Wilk (p-valor)"] > 0.05 else row["Wilcoxon (p-valor)"]
        d_val = row["D de Cohen"]
        d_abs = abs(d_val)
        
        if d_abs < 0.2:
            efecto = "trivial"
        elif d_abs < 0.5:
            efecto = "pequeño"
        elif d_abs < 0.8:
            efecto = "mediano"
        else:
            efecto = "grande"
            
        if active_p < alpha_bonf:
            significant_against_baseline.append(m)
            diff_text = "diferencia estadísticamente significativa"
        else:
            diff_text = "sin diferencia significativa"
            
        interpretations_b1.append(f"**{m}**: {diff_text} frente al modelo baseline (p={active_p:.4f}), efecto {efecto} (D={d_val:.2f}).")
    
    any_significant = len(significant_against_baseline) > 0
    with st.container(border=True):
        st.markdown("##### 🔬 Análisis de Comparaciones Pareadas (sobre T7)")
        interp_pareadas = (
            f"Ningún modelo competidor presenta una diferencia de error estadísticamente significativa frente al modelo baseline ({best_model_name})."
            if not any_significant else
            f"El modelo baseline ({best_model_name}) presenta diferencias estadísticamente significativas frente a modelos competidores."
        )
        explic_pareadas = " ".join(interpretations_b1) + f" (Umbral de significancia corregido por Bonferroni: $\\alpha_{{adj}} = {alpha_bonf:.4f}$)."
        st.markdown(f"**🔍 Interpretación:** {interp_pareadas}\n\n**📖 Explicación:** {explic_pareadas}")
    st.session_state["interpretacion_b1"] = f"{interp_pareadas} {explic_pareadas}"
    
    st.markdown("#### Resultado Final Global")
    try:
        stat_f, p_val_f = stats.friedmanchisquare(*all_fold_maes)
        
        # Calcular Nemenyi antes para cruzar información
        nemenyi_pvals = None
        min_pval = 1.0
        min_pair = ("", "")
        significant_pairs = []
        
        if p_val_f < 0.05:
            import scikit_posthocs as sp
            data = np.array(all_fold_maes).T
            nemenyi_pvals = sp.posthoc_nemenyi_friedman(data)
            nemenyi_pvals.columns = model_names
            nemenyi_pvals.index = model_names
            
            for i in range(len(model_names)):
                for j in range(i+1, len(model_names)):
                    pval = nemenyi_pvals.iloc[i, j]
                    m1, m2 = model_names[i], model_names[j]
                    if pval < min_pval:
                        min_pval = pval
                        min_pair = (m1, m2)
                    if pval < 0.05:
                        significant_pairs.append((m1, m2, pval))
                        
        # Conclusión Friedman
        friedman_conclusion = "Esto indica que no hay evidencia de que los 5 modelos tengan un rendimiento distinto entre sí."
        if p_val_f < 0.05:
            friedman_conclusion = "Esto indica que, al menos, uno de los 5 modelos tiene un rendimiento distinto a los demás, aunque no indica cuál."
            
            # Relación con el baseline
            baseline_in_min_pair = (best_model_name in min_pair)
            
            if not any_significant and not baseline_in_min_pair:
                friedman_conclusion += (
                    f"\n\n**Relación con el modelo ganador:** Esta heterogeneidad detectada por Friedman probablemente no involucra al modelo ganador "
                    f"(**{best_model_name}**), ya que ninguna comparación directa contra él resultó significativa, y el par con mayor diferencia "
                    f"en el análisis post-hoc (**{min_pair[0]}** vs **{min_pair[1]}**, p={min_pval:.3f}) no lo incluye."
                )
            elif baseline_in_min_pair or any_significant:
                razon = "alguna comparación directa contra él resultó estadísticamente significativa en el bloque anterior" if any_significant else f"el par con mayor diferencia en el análisis post-hoc (**{min_pair[0]}** vs **{min_pair[1]}**) lo incluye directamente"
                friedman_conclusion += (
                    f"\n\n**Relación con el modelo ganador:** Esta heterogeneidad podría estar relacionada con el modelo ganador "
                    f"(**{best_model_name}**), ya que {razon}."
                )

        # -------------------------------------------------------------
        # T8 & F9: Rangos Promedio por Modelo (Test de Friedman)
        # -------------------------------------------------------------
        data_folds = np.array(all_fold_maes).T
        ranks_matrix = np.array([stats.rankdata(row) for row in data_folds])
        avg_ranks = np.mean(ranks_matrix, axis=0)

        df_friedman_ranks = pd.DataFrame({
            "Modelo": model_names,
            "Rango Promedio": avg_ranks
        })
        df_friedman_ranks = df_friedman_ranks.sort_values(by="Rango Promedio").reset_index(drop=True)
        df_friedman_ranks["Posición"] = [f"#{i+1}" for i in range(len(df_friedman_ranks))]
        df_friedman_ranks = df_friedman_ranks[["Modelo", "Rango Promedio", "Posición"]]

        st.markdown("##### 📋 Tabla de Rangos Promedio por Modelo (Test de Friedman) (T8)")
        st.dataframe(df_friedman_ranks.style.format({"Rango Promedio": "{:.2f}"}), use_container_width=True, hide_index=True)

        fig_friedman = px.bar(
            df_friedman_ranks,
            x="Modelo",
            y="Rango Promedio",
            color="Rango Promedio",
            color_continuous_scale="Blues_r",
            text="Rango Promedio",
            title="Rangos Promedio de Error por Modelo (Test de Friedman) (F9)",
            template="plotly_dark",
            labels={"Rango Promedio": "Rango Promedio (menor = mejor)", "Modelo": "Modelo de IA"}
        )
        fig_friedman.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_friedman.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0), yaxis=dict(range=[0, len(model_names) + 0.5]))
        st.plotly_chart(fig_friedman, use_container_width=True)

        with st.container(border=True):
            st.markdown("##### 🌐 Análisis de Varianza Global (Test de Friedman)")
            interp_friedman = (
                "El conjunto de modelos exhibe un rendimiento global estadísticamente equivalente sin divergencias significativas."
                if p_val_f >= 0.05 else
                "Se detectó heterogeneidad estadística global significativa entre las arquitecturas evaluadas."
            )
            explic_friedman = (
                f"El Test de Friedman sobre los errores por fold arroja un estadístico $\\chi^2_F = {stat_f:.2f}$ con **p-valor = {p_val_f:.4e}** (umbral $\\alpha = 0.05$). "
                f"Evalúa simultáneamente si las funciones de distribución de error de los {len(model_names)} modelos difieren entre sí. {friedman_conclusion}"
            )
            st.markdown(f"**🔍 Interpretación:** {interp_friedman}\n\n**📖 Explicación:** {explic_friedman}")
        st.session_state["interpretacion_friedman"] = f"{interp_friedman} {explic_friedman}"
        
        # Análisis Post-hoc (Nemenyi)
        st.markdown("### Comparación Post-Hoc (Nemenyi)")
        if p_val_f < 0.05:
            if not significant_pairs:
                interp_nemenyi = "Ningún par de modelos muestra diferencias estadísticamente significativas individuales bajo la prueba conservadora de Nemenyi."
                explic_nemenyi = (
                    f"El par de modelos con la mayor diferencia (p-valor más bajo) es **{min_pair[0]}** vs **{min_pair[1]}** (p={min_pval:.4f}), pero no cruza el umbral de significancia (p < 0.05). "
                    f"Aunque el Test de Friedman detectó heterogeneidad en el conjunto, el control de comparaciones múltiples de Nemenyi confirma que las diferencias entre pares aislados son pequeñas."
                )
            else:
                r2_m1 = results_df[results_df["Modelo"] == min_pair[0]].iloc[0]["CV_R2_Mean"]
                r2_m2 = results_df[results_df["Modelo"] == min_pair[1]].iloc[0]["CV_R2_Mean"]
                mejor = min_pair[0] if r2_m1 > r2_m2 else min_pair[1]
                text_pairs = [f"**{p[0]}** vs **{p[1]}**" for p in significant_pairs]
                interp_nemenyi = f"Se encontraron diferencias estadísticas significativas por pares, con superioridad de **{mejor}** en el contraste principal."
                explic_nemenyi = (
                    f"El par con menor p-valor es **{min_pair[0]}** vs **{min_pair[1]}** (p={min_pval:.4f}, p < 0.05), donde **{mejor}** presenta mayor $R^2$. "
                    f"Pares con diferencias significativas confirmadas: {', '.join(text_pairs)}."
                )
            
            # Tabla T9 (caso con significancia: Matriz de p-valores Post-Hoc Nemenyi)
            st.markdown("##### 📋 Matriz de p-valores Post-Hoc de Nemenyi (T9)")
            st.dataframe(nemenyi_pvals.style.format("{:.4f}"), use_container_width=True)

            # Render Heatmap (F8)
            fig_nemenyi = px.imshow(
                nemenyi_pvals,
                text_auto=".3f",
                color_continuous_scale="RdBu_r",
                title="Matriz de p-valores (Test de Nemenyi) (F8)",
                template="plotly_dark",
                labels=dict(color="p-valor")
            )
            fig_nemenyi.update_layout(height=500, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_nemenyi, use_container_width=True)

            with st.container(border=True):
                st.markdown("##### 📊 Análisis Post-Hoc (Test de Nemenyi)")
                st.markdown(f"**🔍 Interpretación:** {interp_nemenyi}\n\n**📖 Explicación:** {explic_nemenyi}")
            
            # Cache for export
            st.session_state["nemenyi_results"] = {
                "matrix": nemenyi_pvals,
                "text": f"{interp_nemenyi} {explic_nemenyi}"
            }
        else:
            # Tabla T9 (caso sin significancia global: Evidencia empírica de no requerir post-hoc)
            t9_rows = []
            for row in table_data:
                m = row["Modelo de IA"]
                if m == best_model_name:
                    continue
                d_val = row["D de Cohen"]
                d_abs = abs(d_val) if not np.isnan(d_val) else 0.0
                if d_abs < 0.2:
                    efecto = "Trivial (|D| < 0.2)"
                elif d_abs < 0.5:
                    efecto = "Pequeño (0.2 ≤ |D| < 0.5)"
                elif d_abs < 0.8:
                    efecto = "Mediano (0.5 ≤ |D| < 0.8)"
                else:
                    efecto = "Grande (|D| ≥ 0.8)"
                    
                p_active = row["T-Student Apareado (p-valor)"] if row["Shapiro-Wilk (p-valor)"] > 0.05 else row["Wilcoxon (p-valor)"]
                es_signif = "Sí (p < α_adj)" if p_active < alpha_bonf else "No (p ≥ α_adj)"
                
                t9_rows.append({
                    "Modelo": m,
                    "D de Cohen vs. Baseline": d_val,
                    "Magnitud de Efecto": efecto,
                    "¿Significativo?": es_signif
                })
            df_t9 = pd.DataFrame(t9_rows)
            
            st.markdown("##### 📋 Magnitud de Efecto y Significancia vs. Baseline (Filtro Post-Hoc) (T9)")
            st.dataframe(df_t9.style.format({"D de Cohen vs. Baseline": "{:+.4f}"}), use_container_width=True, hide_index=True)

            with st.container(border=True):
                st.markdown("##### 📊 Análisis Post-Hoc (Test de Nemenyi)")
                interp_nemenyi = "No se requiere análisis post-hoc al no detectarse diferencias globales significativas en el test de Friedman."
                explic_nemenyi = f"Dado que el test ómnibus de Friedman no rechazó la hipótesis nula ($p = {p_val_f:.4e} \\ge 0.05$), se asume paridad estadística entre los {len(model_names)} modelos evaluados, descartando comparaciones múltiples redundantes."
                st.markdown(f"**🔍 Interpretación:** {interp_nemenyi}\n\n**📖 Explicación:** {explic_nemenyi}")
            st.session_state["nemenyi_results"] = None

    except ModuleNotFoundError as e:
        if 'scikit_posthocs' in str(e):
            st.error("⚠️ La librería `scikit-posthocs` no está instalada. Para usar el test de Nemenyi, por favor ejecuta el siguiente comando en la terminal:")
            st.code("pip install scikit-posthocs", language="bash")
        else:
            st.warning(f"No se pudo calcular el Test de Friedman/Nemenyi por falta de dependencias: {e}")
        st.session_state["nemenyi_results"] = None
    except Exception as e:
        st.warning(f"No se pudo calcular el Test de Friedman/Nemenyi: {e}")
        st.session_state["nemenyi_results"] = None

    # Veredicto Final
    st.markdown("### Veredicto Final")
    if any_significant:
        modelos_significativos_str = ", ".join([f"**{m}**" for m in significant_against_baseline])
        soporte = f"demostró diferencias estadísticas significativas frente a: {modelos_significativos_str}."
        
        nemenyi_significant_against_baseline = []
        if 'significant_pairs' in locals():
            for m1, m2, pval in significant_pairs:
                if m1 == best_model_name:
                    nemenyi_significant_against_baseline.append(m2)
                elif m2 == best_model_name:
                    nemenyi_significant_against_baseline.append(m1)
                    
        if 'p_val_f' in locals() and p_val_f >= 0.05:
            recomendacion = f"Aunque el modelo ganador (**{best_model_name}**) fue significativamente superior a {modelos_significativos_str} en pruebas pareadas, el Test de Friedman global no detectó heterogeneidad en el conjunto completo de modelos. Por tanto, esta superioridad aislada debe interpretarse con cautela, considerándose el rendimiento global de los modelos como estadísticamente similar en términos estrictos."
        elif len(nemenyi_significant_against_baseline) < len(significant_against_baseline) and len(nemenyi_significant_against_baseline) > 0:
            nem_str = ", ".join([f"**{m}**" for m in nemenyi_significant_against_baseline])
            recomendacion = f"Las pruebas pareadas (T-Student/Wilcoxon) sugieren superioridad frente a {len(significant_against_baseline)} modelo(s), pero el análisis post-hoc más conservador (Nemenyi) solo confirma esta diferencia de forma robusta frente a: {nem_str}. Se recomienda priorizar el resultado de Nemenyi por controlar mejor el error de comparaciones múltiples."
        elif len(nemenyi_significant_against_baseline) == 0:
            recomendacion = f"Las pruebas pareadas (T-Student/Wilcoxon) sugieren superioridad frente a {modelos_significativos_str}, pero el análisis post-hoc más conservador (Nemenyi) NO confirma ninguna diferencia robusta frente al ganador. Se recomienda priorizar el resultado de Nemenyi por controlar mejor el error de comparaciones múltiples."
        else:
            recomendacion = f"Se recomienda usar el modelo ganador (**{best_model_name}**) ya que su elección frente a estos competidores está respaldada estadísticamente de forma consistente en todas las pruebas."
            
        max_d = 0
        min_d = 999
        for row in table_data:
            if row["Modelo de IA"] in significant_against_baseline:
                d = abs(row["D de Cohen"])
                max_d = max(max_d, d)
                min_d = min(min_d, d)
                
        if max_d < 0.3:
            recomendacion += f"\n\n⚠️ **Advertencia de Relevancia Práctica:** Aunque las diferencias son estadísticamente significativas, el tamaño del efecto es trivial-a-pequeño (D de Cohen entre {min_d:.2f} y {max_d:.2f}), lo cual es esperable con un tamaño de muestra Out-of-Fold de {len(best_abs_error)} observaciones y debe interpretarse con cautela en términos de relevancia práctica."
    else:
        extra_desc = " (la heterogeneidad global proviene de contrastes entre otros modelos)" if ('p_val_f' in locals() and p_val_f < 0.05 and 'baseline_in_min_pair' in locals() and not baseline_in_min_pair) else ""
        soporte = f"es estadísticamente similar a los demás modelos evaluados{extra_desc}, a pesar de tener un mejor rendimiento nominal."
        recomendacion = f"Se recomienda usar el modelo ganador (**{best_model_name}**) por su mejor R² y menor error, aunque en la práctica su rendimiento es estadísticamente equivalente a las alternativas."
        
    with st.container(border=True):
        st.markdown("##### 🏆 Veredicto Final de Selección del Modelo")
        interp_veredicto = f"Se ratifica a **{best_model_name}** como el modelo óptimo seleccionado para la plataforma de gemelo digital."
        explic_veredicto = f"El modelo {soporte} **Recomendación:** {recomendacion}"
        st.markdown(f"**🔍 Interpretación:** {interp_veredicto}\n\n**📖 Explicación:** {explic_veredicto}")
    st.session_state["veredicto_final"] = f"{interp_veredicto} {explic_veredicto}"

    st.markdown("---")
    k_folds_num = len(all_fold_maes[0]) if len(all_fold_maes) > 0 else "K"
    st.caption(
        f"**Metodología y rigor:** Para las pruebas T-Student y Wilcoxon, las muestras corresponden a las predicciones Out-of-Fold individuales ({len(best_abs_error)} observaciones). "
        f"Para las pruebas de Friedman y Nemenyi, el análisis se realiza correctamente sobre el error agregado por fold ({k_folds_num} folds), garantizando la comparación entre bloques independientes. "
        f"Se utilizó un nivel de significancia base α=0.05, con **Corrección de Bonferroni** (α_adj={alpha_bonf:.4f}) para comparaciones múltiples. "
        "Si Shapiro-Wilk p > 0.05 (distribución normal), se toma la decisión basada en T-Student. Si p < 0.05 (distribución no normal), se confía en Wilcoxon."
    )
