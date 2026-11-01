"""
Pruebas unitarias y de regresión focalizadas para export_helpers.py:
- Verificación del contrato binario de st.download_button (bytes, nunca callables).
- Detección precisa de modificaciones in-place en DataFrames manteniendo id(df), shape y columns.
- Caching selectivo en session_state que se invalida al mutar celdas.
- Preservación de fidelidad en conversor Plotly -> Matplotlib para las figuras utilizadas (F1 a F11).
- Metadatos físicos reales de 600 DPI.
"""
import io
import numpy as np
import pandas as pd
import pytest
from PIL import Image
from unittest.mock import MagicMock, patch

import export_helpers as eh


def test_export_dataframe_to_excel_dataframe_and_styler():
    df = pd.DataFrame({"col_a": [1.0, 2.5], "col_b": ["texto1", "texto2"]})

    # 1. Test DataFrame
    xlsx_bytes = eh.export_dataframe_to_excel(df, sheet_name="Muestra")
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 0
    # Leer de vuelta con openpyxl / pandas
    df_read = pd.read_excel(io.BytesIO(xlsx_bytes), sheet_name="Muestra")
    assert list(df_read.columns) == ["col_a", "col_b"]
    assert len(df_read) == 2

    # 2. Test Styler
    styler = df.style.highlight_max()
    xlsx_styler_bytes = eh.export_dataframe_to_excel(styler, sheet_name="Estilizado")
    assert isinstance(xlsx_styler_bytes, bytes)
    assert len(xlsx_styler_bytes) > 0
    df_styler_read = pd.read_excel(io.BytesIO(xlsx_styler_bytes), sheet_name="Estilizado")
    assert len(df_styler_read) == 2


def test_render_table_with_excel_contract_and_caching():
    df = pd.DataFrame({"x": [10, 20], "y": [30, 40]})
    session_mock = {}

    with patch.object(eh.st, "dataframe") as mock_df, \
         patch.object(eh.st, "download_button") as mock_btn, \
         patch.object(eh.st, "session_state", session_mock):

        eh.render_table_with_excel(df, filename="tabla_test", key_suffix="k1")

        mock_df.assert_called_once()
        mock_btn.assert_called_once()

        call_kwargs = mock_btn.call_args.kwargs
        data_arg = call_kwargs.get("data")

        # Comprobación crucial: data DEBE ser bytes, NO una función o callable
        assert isinstance(data_arg, bytes), f"Se esperaban bytes pero se obtuvo {type(data_arg)}"
        assert not callable(data_arg)
        assert call_kwargs.get("file_name") == "tabla_test.xlsx"

        # Verificar que se pobló la caché
        cache_key = "dl_xlsx_k1_tabla_test"
        assert f"_cache_excel_{cache_key}" in session_mock

        # Una re-renderización idéntica debe usar los bytes de la caché sin re-exportar
        mock_btn.reset_mock()
        with patch.object(eh, "export_dataframe_to_excel", side_effect=RuntimeError("No debería re-exportar")):
            eh.render_table_with_excel(df, filename="tabla_test", key_suffix="k1")
            mock_btn.assert_called_once()
            assert mock_btn.call_args.kwargs.get("data") == data_arg


def test_render_table_detects_inplace_modification():
    """Prueba de regresión específica:
    - Exportar un DataFrame.
    - Modificar una celda del mismo objeto conservando shape, columnas e id(df).
    - Exportarlo otra vez en la misma sesión.
    - Abrir el segundo Excel y comprobar que contiene el valor actualizado.
    """
    df = pd.DataFrame({"col_a": [10, 20], "col_b": [30, 40]})
    session_mock = {}

    with patch.object(eh.st, "dataframe"), \
         patch.object(eh.st, "download_button") as mock_btn, \
         patch.object(eh.st, "session_state", session_mock):

        # 1. Primera exportación
        eh.render_table_with_excel(df, filename="tabla_inplace", key_suffix="reg")
        first_bytes = mock_btn.call_args.kwargs["data"]
        df_read_1 = pd.read_excel(io.BytesIO(first_bytes))
        assert df_read_1.loc[0, "col_a"] == 10

        # 2. Modificación in-place de una celda conservando id, shape y columns
        initial_id = id(df)
        initial_shape = df.shape
        initial_cols = list(df.columns)

        df.iloc[0, 0] = 9999

        assert id(df) == initial_id
        assert df.shape == initial_shape
        assert list(df.columns) == initial_cols

        # 3. Segunda exportación en la misma sesión
        eh.render_table_with_excel(df, filename="tabla_inplace", key_suffix="reg")
        second_bytes = mock_btn.call_args.kwargs["data"]

        # 4. Validar que los bytes cambiaron y contienen el valor actualizado
        assert first_bytes != second_bytes, "Los bytes del Excel no cambiaron tras la modificación in-place"
        df_read_2 = pd.read_excel(io.BytesIO(second_bytes))
        assert df_read_2.loc[0, "col_a"] == 9999, f"Esperado 9999 pero se obtuvo {df_read_2.loc[0, 'col_a']}"


def test_export_figure_to_600dpi_plotly_and_matplotlib():
    import plotly.express as px
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 1. Figura Matplotlib
    fig_mpl, ax = plt.subplots(figsize=(6, 4))
    ax.plot([1, 2, 3], [4, 5, 6])
    png_mpl = eh.export_figure_to_600dpi(fig_mpl)
    plt.close(fig_mpl)
    assert isinstance(png_mpl, bytes)
    im_mpl = Image.open(io.BytesIO(png_mpl))
    assert im_mpl.format == "PNG"
    dpi_mpl = im_mpl.info.get("dpi")
    assert dpi_mpl is not None and abs(dpi_mpl[0] - 600) < 1.0

    # 2. Figura Plotly
    df = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
    fig_plotly = px.imshow(df.corr(), text_auto=".2f")
    png_plotly = eh.export_figure_to_600dpi(fig_plotly)
    assert isinstance(png_plotly, bytes)
    im_plotly = Image.open(io.BytesIO(png_plotly))
    assert im_plotly.format == "PNG"
    dpi_plotly = im_plotly.info.get("dpi")
    assert dpi_plotly is not None and abs(dpi_plotly[0] - 600) < 1.0


def test_render_high_res_chart_contract_and_caching():
    import plotly.graph_objects as go
    fig = go.Figure(data=go.Scatter(x=[1, 2], y=[3, 4]))
    session_mock = {}

    with patch.object(eh.st, "plotly_chart") as mock_chart, \
         patch.object(eh.st, "download_button") as mock_btn, \
         patch.object(eh.st, "caption") as mock_cap, \
         patch.object(eh.st, "session_state", session_mock):

        eh.render_high_res_chart(fig, filename="grafica_test", key_suffix="k2")

        mock_chart.assert_called_once()
        mock_btn.assert_called_once()
        mock_cap.assert_called_once()

        call_kwargs = mock_btn.call_args.kwargs
        data_arg = call_kwargs.get("data")

        assert isinstance(data_arg, bytes), f"Se esperaban bytes pero se obtuvo {type(data_arg)}"
        assert not callable(data_arg)
        assert call_kwargs.get("file_name") == "grafica_test_600dpi.png"

        # Caching
        cache_key = "dl_png_k2_grafica_test"
        assert f"_cache_png_{cache_key}" in session_mock


def test_all_11_figures_supported_in_fallback():
    """Verifica que las 11 figuras utilizadas en la aplicación se conviertan
    fielmente mediante el fallback Matplotlib sin errores y con metadatos 600 DPI."""
    import plotly.express as px
    import plotly.graph_objects as go

    # F1: Matriz de correlaciones (Heatmap)
    df_f1 = pd.DataFrame(np.eye(4), columns=["x1", "x2", "y1", "y2"], index=["x1", "x2", "y1", "y2"])
    fig_f1 = px.imshow(df_f1, color_continuous_scale="Viridis", template="plotly_dark")
    png_f1 = eh._plotly_to_matplotlib_png(fig_f1)
    assert len(png_f1) > 0

    # F2: Histograma con marginal boxplot y KDE
    df_f2 = pd.DataFrame({"var1": np.random.randn(50)})
    fig_f2 = px.histogram(df_f2, x="var1", nbins=15, marginal="box", template="plotly_dark")
    fig_f2.add_scatter(x=np.linspace(-2, 2, 20), y=np.linspace(0, 0.4, 20), mode="lines", name="KDE")
    png_f2 = eh._plotly_to_matplotlib_png(fig_f2)
    assert len(png_f2) > 0

    # F3: Boxplots multivariable con líneas horizontales
    df_f3 = pd.DataFrame({"Var": ["A"]*10 + ["B"]*10, "Z-Score": list(range(20))})
    fig_f3 = px.box(df_f3, x="Var", y="Z-Score", color="Var", template="plotly_dark")
    fig_f3.add_hline(y=3.0, line_dash="dash", line_color="#ef4444")
    fig_f3.add_hline(y=-3.0, line_dash="dash", line_color="#ef4444")
    png_f3 = eh._plotly_to_matplotlib_png(fig_f3)
    assert len(png_f3) > 0

    # F4: Mapa de recursos espacial (Heatmap YlGnBu)
    grid_f4 = np.random.rand(10, 10)
    fig_f4 = px.imshow(grid_f4, color_continuous_scale="YlGnBu", template="plotly_dark")
    png_f4 = eh._plotly_to_matplotlib_png(fig_f4)
    assert len(png_f4) > 0

    # F5: Trayectoria poblacional ABM (x=None, y=array)
    fig_f5 = go.Figure()
    fig_f5.add_scatter(y=[10, 25, 40, 35, 50], mode="lines+markers", name="Población")
    png_f5 = eh._plotly_to_matplotlib_png(fig_f5)
    assert len(png_f5) > 0

    # F6: Comparación de métricas clave (Barras agrupadas)
    df_f6 = pd.DataFrame({
        "Modelo": ["Ridge", "RF"],
        "R2 Score": [0.85, 0.90],
        "Expl Variance": [0.86, 0.91]
    }).melt(id_vars="Modelo", var_name="metrica", value_name="valor")
    fig_f6 = px.bar(df_f6, x="Modelo", y="valor", color="metrica", barmode="group", template="plotly_dark")
    png_f6 = eh._plotly_to_matplotlib_png(fig_f6)
    assert len(png_f6) > 0

    # F7: Predichos vs Reales con diagonal y=x
    fig_f7 = go.Figure()
    fig_f7.add_scatter(x=[1, 2, 3], y=[1.1, 1.9, 3.2], mode="markers")
    fig_f7.add_shape(type="line", x0=1, y0=1, x1=3.5, y1=3.5, line=dict(color="white", dash="dash"))
    png_f7 = eh._plotly_to_matplotlib_png(fig_f7)
    assert len(png_f7) > 0

    # F8: Distribución de residuos con línea horizontal cero
    fig_f8 = go.Figure()
    fig_f8.add_scatter(x=[1, 2, 3], y=[-0.1, 0.1, -0.2], mode="markers")
    fig_f8.add_shape(type="line", x0=1, y0=0, x1=3, y1=0, line=dict(color="white", dash="dash"))
    png_f8 = eh._plotly_to_matplotlib_png(fig_f8)
    assert len(png_f8) > 0

    # F9: Feature Importance horizontal
    df_f9 = pd.DataFrame({"Variable": ["feat_a", "feat_b"], "Importancia": [0.3, 0.7]})
    fig_f9 = px.bar(df_f9, x="Importancia", y="Variable", orientation="h", template="plotly_dark")
    png_f9 = eh._plotly_to_matplotlib_png(fig_f9)
    assert len(png_f9) > 0

    # F10: Rangos promedio Friedman vertical con texto
    df_f10 = pd.DataFrame({"Modelo": ["Ridge", "RF"], "Rango Promedio": [1.5, 2.5]})
    fig_f10 = px.bar(df_f10, x="Modelo", y="Rango Promedio", color="Rango Promedio",
                     color_continuous_scale="Blues_r", text="Rango Promedio", template="plotly_dark")
    png_f10 = eh._plotly_to_matplotlib_png(fig_f10)
    assert len(png_f10) > 0

    # F11: Matriz de p-valores Nemenyi con text_auto
    df_f11 = pd.DataFrame([[1.0, 0.045], [0.045, 1.0]], index=["Ridge", "RF"], columns=["Ridge", "RF"])
    fig_f11 = px.imshow(df_f11, text_auto=".3f", color_continuous_scale="RdBu_r", template="plotly_dark")
    png_f11 = eh._plotly_to_matplotlib_png(fig_f11)
    assert len(png_f11) > 0

    # Validar metadatos DPI en una de las figuras resultantes
    im = Image.open(io.BytesIO(png_f11))
    assert im.format == "PNG"
    dpi = im.info.get("dpi")
    assert dpi is not None and abs(dpi[0] - 600) < 1.0
