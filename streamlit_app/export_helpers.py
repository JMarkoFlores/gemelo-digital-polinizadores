"""
Módulo de utilidades de exportación para Streamlit:
- Exportación de figuras (Plotly / Matplotlib) en Ultra Alta Resolución (600 DPI reales con metadatos).
- Exportación de tablas (DataFrames / Stylers) a Microsoft Excel (.xlsx).
"""
from __future__ import annotations

import io
import re
from typing import Any
from PIL import Image
import pandas as pd
import streamlit as st


def get_high_res_plotly_config(filename: str = "grafica_600dpi") -> dict:
    """Configuración para exportar imágenes a ultra-alta resolución (600 DPI mínimo)
    desde el botón de cámara (modebar) de Plotly en el navegador."""
    clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", filename).strip("_") or "grafica"
    return {
        "toImageButtonOptions": {
            "format": "png",
            "filename": f"{clean_name}_600dpi",
            "height": 2200,
            "width": 3800,
            "scale": 4,
        },
        "displaylogo": False,
        "modeBarButtonsToAdd": ["downloadSVG"],
    }


def export_figure_to_600dpi(fig: Any) -> bytes:
    """Convierte una figura de Plotly o Matplotlib a formato PNG con metadatos de resolución física de 600 DPI."""
    buf = io.BytesIO()
    if hasattr(fig, "to_image"):
        # Figura Plotly
        w = getattr(fig.layout, "width", None) or 1200
        h = getattr(fig.layout, "height", None) or 700
        try:
            raw_png = fig.to_image(format="png", scale=4, width=w, height=h)
        except Exception:
            raw_png = fig.to_image(format="png", scale=4)
        im = Image.open(io.BytesIO(raw_png))
        im.save(buf, format="PNG", dpi=(600, 600))
        return buf.getvalue()
    elif hasattr(fig, "savefig"):
        # Figura Matplotlib
        fig.savefig(buf, format="png", dpi=600, bbox_inches="tight")
        return buf.getvalue()
    else:
        raise ValueError("El objeto de figura proporcionado no es compatible con Plotly ni con Matplotlib.")


def render_high_res_chart(fig: Any, filename: str, key_suffix: str = "") -> None:
    """Renderiza el gráfico Plotly en Streamlit configurado a 600 DPI
    y ofrece un botón para descargarlo directamente en ultra-alta resolución (600 DPI PNG con metadatos reales)."""
    clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", filename).strip("_") or "grafica"
    config = get_high_res_plotly_config(clean_name)
    st.plotly_chart(fig, use_container_width=True, config=config)

    btn_key = f"dl_png_{key_suffix}_{clean_name}"

    def _data_callable() -> bytes:
        return export_figure_to_600dpi(fig)

    st.download_button(
        label="📥 Descargar imagen en Alta Resolución (600 DPI PNG)",
        data=_data_callable,
        file_name=f"{clean_name}_600dpi.png",
        mime="image/png",
        key=btn_key,
        help="Descarga directa de esta figura en ultra-alta definición con metadatos de 600 DPI para publicación científica.",
    )


def export_dataframe_to_excel(df: Any, sheet_name: str = "Datos", include_index: bool = False) -> bytes:
    """Convierte un DataFrame o Styler de pandas a archivo binario Excel (.xlsx) con openpyxl."""
    buf = io.BytesIO()
    # Si es un Styler de pandas (formateado con .style)
    if hasattr(df, "data") and hasattr(df, "to_excel"):
        try:
            df.to_excel(buf, sheet_name=sheet_name[:31], index=include_index, engine="openpyxl")
            return buf.getvalue()
        except TypeError:
            try:
                df.to_excel(buf, sheet_name=sheet_name[:31], engine="openpyxl")
                return buf.getvalue()
            except Exception:
                df.data.to_excel(buf, sheet_name=sheet_name[:31], index=include_index, engine="openpyxl")
                return buf.getvalue()
        except Exception:
            df.data.to_excel(buf, sheet_name=sheet_name[:31], index=include_index, engine="openpyxl")
            return buf.getvalue()
    elif isinstance(df, pd.DataFrame):
        df.to_excel(buf, sheet_name=sheet_name[:31], index=include_index, engine="openpyxl")
        return buf.getvalue()
    else:
        pd.DataFrame(df).to_excel(buf, sheet_name=sheet_name[:31], index=include_index, engine="openpyxl")
        return buf.getvalue()


def render_table_with_excel(
    df: Any,
    filename: str,
    key_suffix: str = "",
    sheet_name: str = "Datos",
    include_index: bool = False,
    hide_index: bool | None = None,
    column_config: dict | None = None,
    use_container_width: bool = True,
    help_text: str | None = None,
) -> None:
    """Renderiza una tabla en Streamlit (st.dataframe) y añade un botón
    para descargarla directamente en formato Microsoft Excel (.xlsx)."""
    df_kwargs: dict[str, Any] = {"use_container_width": use_container_width}
    if hide_index is not None:
        df_kwargs["hide_index"] = hide_index
    if column_config is not None:
        df_kwargs["column_config"] = column_config

    st.dataframe(df, **df_kwargs)

    clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", filename).strip("_") or "tabla"
    btn_key = f"dl_xlsx_{key_suffix}_{clean_name}"

    def _excel_callable() -> bytes:
        return export_dataframe_to_excel(df, sheet_name=sheet_name, include_index=include_index)

    st.download_button(
        label="📥 Descargar tabla en Excel (.xlsx)",
        data=_excel_callable,
        file_name=f"{clean_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=btn_key,
        help=help_text or f"Descarga la tabla '{clean_name}' en formato Microsoft Excel (.xlsx).",
    )
