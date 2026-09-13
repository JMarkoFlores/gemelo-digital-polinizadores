import re

with open("streamlit_app/app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Locate the end of the c_chart2 block
target = """                fig_res.add_shape(type="line", x0=last_y_pred[:, 0].min(), y0=0, x1=last_y_pred[:, 0].max(), y1=0, line=dict(color="white", dash="dash"))
                fig_res.update_layout(template="plotly_dark", height=280, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Valores Predichos", yaxis_title="Error Residual")
                st.plotly_chart(fig_res, use_container_width=True)"""

addition = """
        # Bootstrap CI & Feature Importance
        st.markdown("<br>### Análisis de Fiabilidad e Importancia (Modelo Ganador)", unsafe_allow_html=True)
        if selected_model == best_overall:
            with st.spinner("Calculando intervalos de confianza (Bootstrap) e importancia de variables..."):
                # Bootstrap
                n_bootstraps = 500
                boot_r2 = []
                boot_mae = []
                boot_rmse = []
                n_samples = len(last_y_true)
                for _ in range(n_bootstraps):
                    idx = np.random.choice(np.arange(n_samples), size=n_samples, replace=True)
                    y_t_boot = last_y_true[idx, 0]
                    y_p_boot = last_y_pred[idx, 0]
                    boot_r2.append(r2_score(y_t_boot, y_p_boot))
                    boot_mae.append(mean_absolute_error(y_t_boot, y_p_boot))
                    boot_rmse.append(np.sqrt(mean_squared_error(y_t_boot, y_p_boot)))
                
                ci_r2 = np.percentile(boot_r2, [2.5, 97.5])
                ci_mae = np.percentile(boot_mae, [2.5, 97.5])
                ci_rmse = np.percentile(boot_rmse, [2.5, 97.5])
                
                c_ci1, c_ci2, c_ci3 = st.columns(3)
                with c_ci1:
                    st.info(f"**R² (IC 95%)**\\n\\n[{ci_r2[0]:.3f}, {ci_r2[1]:.3f}]")
                with c_ci2:
                    st.info(f"**MAE (IC 95%)**\\n\\n[{ci_mae[0]:.3f}, {ci_mae[1]:.3f}]")
                with c_ci3:
                    st.info(f"**RMSE (IC 95%)**\\n\\n[{ci_rmse[0]:.3f}, {ci_rmse[1]:.3f}]")
                
                # Permutation Feature Importance
                st.markdown("**Importancia de Variables (Estimación basada en Permutation MAE en validación)**")
                model_obj = sel_row.get("last_model")
                last_X_val = sel_row.get("last_X_val")
                
                importances = []
                if last_X_val is not None:
                    try:
                        base_preds = last_y_pred
                        base_mae = mean_absolute_error(last_y_true[:, 0], base_preds[:, 0])
                        for i, feat in enumerate(FEATURE_COLUMNS):
                            X_perm = last_X_val.copy()
                            np.random.shuffle(X_perm[:, i])
                            if "dnn" in selected_model.lower() or "autoencoder" in selected_model.lower():
                                p_scaled = model_obj.predict(X_perm, verbose=0)
                                p_perm = training_result["target_scaler"].inverse_transform(p_scaled)
                            else:
                                p_scaled = model_obj.predict(X_perm)
                                p_perm = training_result["target_scaler"].inverse_transform(p_scaled)
                            
                            perm_mae = mean_absolute_error(last_y_true[:, 0], p_perm[:, 0])
                            importances.append(max(0, perm_mae - base_mae))
                            
                        # Normalize
                        sum_imp = sum(importances) + 1e-9
                        importances = [imp / sum_imp for imp in importances]
                        
                        df_imp = pd.DataFrame({"Variable": FEATURE_COLUMNS, "Importancia": importances}).sort_values("Importancia", ascending=True)
                        fig_imp = px.bar(df_imp, x="Importancia", y="Variable", orientation='h', title="Feature Importance (Permutation MAE)")
                        fig_imp.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=30, b=0))
                        st.plotly_chart(fig_imp, use_container_width=True)
                    except Exception as e:
                        st.warning(f"No se pudo calcular la importancia de variables: {str(e)}")
        else:
            st.info("ℹ️ Selecciona el modelo ganador para visualizar sus intervalos de confianza e importancia de variables.")
"""

new_content = content.replace(target, target + "\n" + addition)
with open("streamlit_app/app.py", "w", encoding="utf-8") as f:
    f.write(new_content)
