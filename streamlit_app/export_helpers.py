"""
Módulo de utilidades de exportación para Streamlit:
- Exportación de figuras (Plotly / Matplotlib) en Ultra Alta Resolución (600 DPI reales con metadatos).
- Exportación de tablas (DataFrames / Stylers) a Microsoft Excel (.xlsx).
"""
from __future__ import annotations

import hashlib
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


def _resolve_color(color_obj: Any, default_color: str, cmap: Any = None) -> Any:
    """Resuelve de forma segura colores que pueden ser cadenas individuales,
    listas o arreglos de NumPy (escalas continuas o paletas por barra)."""
    import numpy as np
    if color_obj is None:
        return default_color
    if isinstance(color_obj, str):
        return color_obj
    if isinstance(color_obj, (list, tuple, np.ndarray)):
        try:
            arr = np.array(color_obj)
            if np.issubdtype(arr.dtype, np.number):
                if cmap is not None and len(arr) > 0:
                    amin, amax = float(arr.min()), float(arr.max())
                    denom = (amax - amin) if amax > amin else 1.0
                    norm_vals = [(float(v) - amin) / denom for v in arr]
                    return [cmap(v) for v in norm_vals]
                return default_color
            return list(color_obj)
        except Exception:
            return default_color
    return default_color


def _get_matplotlib_cmap(colorscale_obj: Any, is_dark: bool = False):
    """Extrae o mapea una escala de color de Plotly a un objeto Colormap de Matplotlib."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    # 1. Si viene como lista de tuplas [(0.0, 'rgb(...)'), (1.0, ...)]
    if isinstance(colorscale_obj, (list, tuple)) and len(colorscale_obj) > 0:
        if isinstance(colorscale_obj[0], (list, tuple)) and len(colorscale_obj[0]) == 2:
            try:
                def parse_color(c: Any):
                    m = re.match(r"rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)", str(c))
                    if m:
                        return (float(m.group(1)) / 255.0, float(m.group(2)) / 255.0, float(m.group(3)) / 255.0)
                    return str(c)

                scale_colors = [(float(pos), parse_color(col)) for pos, col in colorscale_obj]
                return LinearSegmentedColormap.from_list("plotly_scale", scale_colors)
            except Exception:
                pass

    # 2. Si viene como nombre de escala string
    scale_name = str(colorscale_obj or "").lower().strip()
    name_map = {
        "viridis": "viridis",
        "ylgnbu": "YlGnBu",
        "ylgn": "YlGn",
        "blues_r": "Blues_r",
        "blues": "Blues",
        "rdbu_r": "RdBu_r",
        "rdbu": "RdBu",
        "rdylgn": "RdYlGn",
        "magma": "magma",
        "plasma": "plasma",
        "inferno": "inferno",
        "cividis": "cividis",
    }
    for k, v in name_map.items():
        if k in scale_name:
            try:
                return plt.get_cmap(v)
            except Exception:
                pass

    if scale_name:
        try:
            return plt.get_cmap(colorscale_obj)
        except Exception:
            pass

    return plt.get_cmap("viridis" if is_dark else "Blues")


def _plotly_to_matplotlib_png(fig: Any, width: int = 1200, height: int = 700) -> bytes:
    """Convierte una figura de Plotly a imagen PNG de alta fidelidad mediante Matplotlib
    cuando el motor estático nativo (Kaleido / Chrome headless) no está disponible en el contenedor.
    
    Preserva datos, series, escalas, etiquetas, correspondencia espacial de matrices/heatmaps,
    distribuciones marginales y anotaciones estructurales."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    w_in = max(6.0, (width or 1200) / 150.0)
    h_in = max(4.0, (height or 700) / 150.0)

    # 1. Detectar preferencia de tema oscuro
    template = getattr(fig.layout, "template", None)
    is_dark = False
    if template and hasattr(template, "layout") and template.layout.paper_bgcolor:
        bg = str(template.layout.paper_bgcolor).lower()
        if "dark" in bg or bg.startswith("#1") or bg.startswith("#2"):
            is_dark = True
    elif hasattr(fig.layout, "paper_bgcolor") and fig.layout.paper_bgcolor:
        bg = str(fig.layout.paper_bgcolor).lower()
        if "dark" in bg or bg.startswith("#1") or bg.startswith("#2"):
            is_dark = True

    traces = list(getattr(fig, "data", []))

    # 2. Detectar si es un gráfico compuesto con marginal (e.g. F2: histograma con marginal boxplot)
    has_marginal_box = any(
        getattr(t, "type", None) == "box" and getattr(t, "yaxis", None) in ("y2", "yaxis2")
        for t in traces
    ) and any(getattr(t, "type", None) == "histogram" for t in traces)

    if has_marginal_box:
        fig_mpl, (ax_box, ax) = plt.subplots(
            2, 1, figsize=(w_in, h_in), sharex=True,
            gridspec_kw={"height_ratios": [0.18, 0.82], "hspace": 0.06}, dpi=600
        )
        axes_list = [ax_box, ax]
    else:
        fig_mpl, ax = plt.subplots(figsize=(w_in, h_in), dpi=600)
        ax_box = None
        axes_list = [ax]

    # Aplicar estilos de tema a los ejes
    for target_ax in axes_list:
        if is_dark:
            fig_mpl.patch.set_facecolor("#0e1117")
            target_ax.set_facecolor("#1e2129")
            target_ax.tick_params(colors="white")
            target_ax.xaxis.label.set_color("white")
            target_ax.yaxis.label.set_color("white")
            target_ax.title.set_color("white")
            for spine in target_ax.spines.values():
                spine.set_color("#44475a")

    has_rendered = False

    # 3. Extraer configuración de coloraxis compartida si existe
    coloraxis_scale = None
    coloraxis_cmin = None
    coloraxis_cmax = None
    coloraxis_obj = getattr(fig.layout, "coloraxis", None)
    if coloraxis_obj:
        coloraxis_scale = getattr(coloraxis_obj, "colorscale", None)
        coloraxis_cmin = getattr(coloraxis_obj, "cmin", None)
        coloraxis_cmax = getattr(coloraxis_obj, "cmax", None)

    # 4. Procesamiento de traces según tipo
    ttypes = [getattr(t, "type", None) for t in traces]

    # --- CASO A: HISTOGRAMA CON BOXPLOT MARGINAL (F2) ---
    if has_marginal_box and ax_box is not None:
        box_trace = [t for t in traces if getattr(t, "type", None) == "box"][0]
        hist_trace = [t for t in traces if getattr(t, "type", None) == "histogram"][0]
        scatter_traces = [t for t in traces if getattr(t, "type", None) == "scatter"]

        # Boxplot superior
        box_data = list(box_trace.x) if box_trace.x is not None else (list(box_trace.y) if box_trace.y is not None else [])
        clean_box_data = [float(v) for v in box_data if v is not None and not np.isnan(v)]
        if clean_box_data:
            try:
                ax_box.boxplot(clean_box_data, orientation="horizontal", patch_artist=True,
                               boxprops=dict(facecolor="#38bdf8", alpha=0.7),
                               medianprops=dict(color="white" if is_dark else "black", linewidth=1.5))
            except TypeError:
                ax_box.boxplot(clean_box_data, vert=False, patch_artist=True,
                               boxprops=dict(facecolor="#38bdf8", alpha=0.7),
                               medianprops=dict(color="white" if is_dark else "black", linewidth=1.5))
        ax_box.axis("off")

        # Histograma inferior
        hx = list(hist_trace.x) if hist_trace.x is not None else []
        clean_hx = [float(v) for v in hx if v is not None and not np.isnan(v)]
        nbins = getattr(hist_trace, "nbinsx", 25) or 25
        is_density = getattr(hist_trace, "histnorm", None) == "probability density"
        ax.hist(clean_hx, bins=min(nbins, 30), density=is_density, color="#38bdf8", alpha=0.75,
                edgecolor="white" if is_dark else "black", label=getattr(hist_trace, "name", "Frecuencia"))

        # KDE scatter superpuesto
        for st_tr in scatter_traces:
            sx = list(st_tr.x) if st_tr.x is not None else []
            sy = list(st_tr.y) if st_tr.y is not None else []
            s_name = getattr(st_tr, "name", "KDE")
            line_cfg = getattr(st_tr, "line", None)
            l_color = getattr(line_cfg, "color", "#f59e0b") if line_cfg else "#f59e0b"
            l_width = getattr(line_cfg, "width", 2.0) if line_cfg else 2.0
            ax.plot(sx, sy, color=l_color, linewidth=l_width, label=s_name)

        has_rendered = True

    # --- CASO B: HEATMAPS (F1, F4, F11) ---
    elif "heatmap" in ttypes:
        heat_trace = [t for t in traces if getattr(t, "type", None) == "heatmap"][0]
        z_raw = getattr(heat_trace, "z", None)
        z = np.array(z_raw, dtype=float) if z_raw is not None else None

        if z is not None and z.size > 0:
            scale_source = coloraxis_scale or getattr(heat_trace, "colorscale", None)
            cmap = _get_matplotlib_cmap(scale_source, is_dark=is_dark)

            vmin = coloraxis_cmin if coloraxis_cmin is not None else getattr(heat_trace, "zmin", None)
            vmax = coloraxis_cmax if coloraxis_cmax is not None else getattr(heat_trace, "zmax", None)

            im = ax.imshow(z, origin="upper", cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)

            # Ticks en columnas (X)
            tx = getattr(heat_trace, "x", None)
            if tx is not None and len(tx) == z.shape[1]:
                ax.set_xticks(range(len(tx)))
                rot = 45 if len(tx) > 4 else 0
                sz = 8 if len(tx) > 8 else 10
                ax.set_xticklabels([str(x_val) for x_val in tx], rotation=rot, ha="right", fontsize=sz)

            # Ticks en filas (Y)
            ty = getattr(heat_trace, "y", None)
            if ty is not None and len(ty) == z.shape[0]:
                ax.set_yticks(range(len(ty)))
                sz = 8 if len(ty) > 8 else 10
                ax.set_yticklabels([str(y_val) for y_val in ty], fontsize=sz)

            # Barra de color
            cbar = fig_mpl.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            if is_dark:
                cbar.ax.yaxis.set_tick_params(color="white")
                plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="white")

            # Texto en celdas (F11 Nemenyi / F1 Correlaciones)
            text_data = getattr(heat_trace, "text", None)
            text_tmpl = getattr(heat_trace, "texttemplate", None)
            text_auto = getattr(heat_trace, "textauto", False)

            if text_data is not None or text_tmpl or text_auto:
                ny, nx = z.shape
                for r in range(ny):
                    for c in range(nx):
                        cell_val = z[r, c]
                        val_str = ""
                        if text_data is not None:
                            try:
                                val_str = str(text_data[r][c])
                            except Exception:
                                pass
                        elif text_tmpl:
                            fmt_m = re.search(r"%\{z:([^}]+)\}", str(text_tmpl))
                            if fmt_m:
                                try:
                                    val_str = format(cell_val, fmt_m.group(1))
                                except Exception:
                                    val_str = f"{cell_val:.3f}"
                            else:
                                val_str = f"{cell_val:.3f}"
                        elif text_auto:
                            val_str = f"{cell_val:.3f}"

                        if val_str:
                            try:
                                norm_v = im.norm(cell_val)
                                rgba = im.cmap(norm_v)
                                lum = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
                                txt_c = "white" if lum < 0.45 else "black"
                            except Exception:
                                txt_c = "white" if is_dark else "black"
                            f_sz = 8 if max(nx, ny) > 6 else 10
                            ax.text(c, r, val_str, ha="center", va="center", color=txt_c, fontsize=f_sz, fontweight="normal")

            has_rendered = True

    # --- CASO C: BARRAS AGRUPADAS O INDIVIDUALES (F6, F9, F10) ---
    elif "bar" in ttypes:
        bar_traces = [t for t in traces if getattr(t, "type", None) == "bar"]
        barmode = getattr(fig.layout, "barmode", "group")

        if len(bar_traces) > 1 and barmode == "group":
            # Gráfico de barras agrupadas (F6)
            n_groups = len(bar_traces)
            total_w = 0.8
            bar_w = total_w / n_groups
            cats = list(bar_traces[0].x) if getattr(bar_traces[0], "x", None) is not None else []
            indices = np.arange(len(cats))
            palette = ["#73b0ff", "#ffbaba", "#38bdf8", "#4ade80", "#f472b6"]

            for i, bt in enumerate(bar_traces):
                offset = (i - (n_groups - 1) / 2.0) * bar_w
                pos = indices + offset
                y_vals = [float(v) if v is not None else 0.0 for v in bt.y]
                c = _resolve_color(getattr(getattr(bt, "marker", None), "color", None), palette[i % len(palette)])
                lbl = getattr(bt, "name", None) or f"Serie {i+1}"
                ax.bar(pos, y_vals, width=bar_w, color=c, label=lbl, alpha=0.9)

            ax.set_xticks(indices)
            ax.set_xticklabels([str(c) for c in cats], rotation=25, ha="right", fontsize=9)
            has_rendered = True

        else:
            # Gráficos de barras individuales (F9 horizontal / F10 vertical)
            scale_source = coloraxis_scale or getattr(fig.layout, "coloraxis", None)
            cmap_bar = _get_matplotlib_cmap(scale_source, is_dark=is_dark)
            for bt in bar_traces:
                x = list(bt.x) if bt.x is not None else []
                y = list(bt.y) if bt.y is not None else []
                orient = getattr(bt, "orientation", "v")
                default_c = "#4a90e2" if not is_dark else "#73b0ff"
                c = _resolve_color(getattr(getattr(bt, "marker", None), "color", None), default_c, cmap=cmap_bar)

                if orient == "h":
                    ax.barh(y, x, color=c, alpha=0.85)
                    ax.set_yticks(range(len(y)))
                    ax.set_yticklabels([str(val) for val in y], fontsize=9)
                else:
                    ax.bar(range(len(x)), y, color=c, alpha=0.85)
                    ax.set_xticks(range(len(x)))
                    ax.set_xticklabels([str(val) for val in x], rotation=25, ha="right", fontsize=9)
                    # Text labels encima de barras (F10)
                    t_vals = getattr(bt, "text", None)
                    if t_vals is not None and len(t_vals) == len(y):
                        max_y = max(y) if len(y) > 0 else 1.0
                        for xi, yi, tv in zip(range(len(x)), y, t_vals):
                            txt_label = f"{float(tv):.2f}" if isinstance(tv, (int, float)) else str(tv)
                            ax.text(xi, yi + (0.02 * max_y), txt_label, ha="center", va="bottom",
                                    fontsize=8, color="white" if is_dark else "black")
            has_rendered = True

    # --- CASO D: BOXPLOTS MULTI-VARIABLE O INDIVIDUAL (F3) ---
    elif "box" in ttypes:
        box_traces = [t for t in traces if getattr(t, "type", None) == "box"]
        all_box_data = []
        all_box_labels = []
        for i, bt in enumerate(box_traces):
            y_raw = getattr(bt, "y", None)
            clean_vals = [float(v) for v in y_raw if v is not None and not np.isnan(v)] if y_raw is not None else []
            x_raw = getattr(bt, "x", None)
            lbl = getattr(bt, "name", None) or (x_raw[0] if x_raw is not None and len(x_raw) > 0 else f"Var {i+1}")
            all_box_data.append(clean_vals)
            all_box_labels.append(lbl)

        if all_box_data:
            bp = ax.boxplot(all_box_data, patch_artist=True)
            box_palette = ["#a78bfa", "#38bdf8", "#34d399", "#fbbf24", "#f87171", "#818cf8", "#4ade80", "#fb923c", "#f472b6"]
            for i, patch in enumerate(bp.get("boxes", [])):
                patch.set_facecolor(box_palette[i % len(box_palette)])
                patch.set_alpha(0.7)
            ax.set_xticks(range(1, len(all_box_labels) + 1))
            ax.set_xticklabels(all_box_labels, rotation=35, ha="right", fontsize=8)
        has_rendered = True

    # --- CASO E: SCATTER / LÍNEAS / RESIDUOS (F5, F7, F8) ---
    elif "scatter" in ttypes:
        for st_tr in traces:
            if getattr(st_tr, "type", None) != "scatter":
                continue
            y = list(st_tr.y) if st_tr.y is not None else []
            # Garantizar dimensión coincidente cuando x es None (como en F5 trayectoria poblacional)
            x = list(st_tr.x) if st_tr.x is not None else list(range(len(y)))

            mode = getattr(st_tr, "mode", "lines") or "lines"
            lbl = getattr(st_tr, "name", None)
            m_color = _resolve_color(getattr(getattr(st_tr, "marker", None), "color", None), ("#73b0ff" if is_dark else "#1d4ed8"))
            l_color = _resolve_color(getattr(getattr(st_tr, "line", None), "color", None), ("#22c55e" if is_dark else "#16a34a"))
            l_width = getattr(getattr(st_tr, "line", None), "width", 2.0)

            if "lines" in mode and "markers" in mode:
                ax.plot(x, y, "-o", color=l_color, markerfacecolor=m_color, linewidth=l_width, label=lbl)
            elif "lines" in mode:
                ax.plot(x, y, "-", color=l_color, linewidth=l_width, label=lbl)
            else:
                alpha = getattr(getattr(st_tr, "marker", None), "opacity", 0.75) or 0.75
                ax.scatter(x, y, color=m_color, alpha=alpha, label=lbl, s=30)
            has_rendered = True

    # 5. Anotaciones de formas geométricas / líneas de referencia (F3 ±3σ, F7 diagonal y=x, F8 cero)
    shapes = list(getattr(fig.layout, "shapes", []))
    for shape in shapes:
        stype = getattr(shape, "type", "line")
        x0, y0, x1, y1 = getattr(shape, "x0", None), getattr(shape, "y0", None), getattr(shape, "x1", None), getattr(shape, "y1", None)
        line_cfg = getattr(shape, "line", None) or {}
        l_dash = getattr(line_cfg, "dash", "solid") if hasattr(line_cfg, "dash") else line_cfg.get("dash", "solid")
        l_color = getattr(line_cfg, "color", "white" if is_dark else "#444444") if hasattr(line_cfg, "color") else line_cfg.get("color", "white" if is_dark else "#444444")
        ls = "--" if "dash" in str(l_dash).lower() else "-"

        if stype == "line" and y0 is not None and y1 is not None:
            if y0 == y1:
                # Línea horizontal de referencia
                ax.axhline(y=float(y0), linestyle=ls, color=str(l_color), linewidth=1.5, alpha=0.85)
            elif x0 is not None and x1 is not None:
                # Línea entre dos puntos coordenados (e.g. diagonal y=x en F7)
                ax.plot([float(x0), float(x1)], [float(y0), float(y1)], linestyle=ls, color=str(l_color), linewidth=1.5, alpha=0.85)

    # 6. Títulos, etiquetas de ejes y leyendas
    if hasattr(fig.layout, "title") and fig.layout.title and getattr(fig.layout.title, "text", None):
        target_title_ax = ax_box if ax_box is not None else ax
        target_title_ax.set_title(str(fig.layout.title.text), fontsize=11, pad=10)
    if hasattr(fig.layout, "xaxis") and fig.layout.xaxis and getattr(fig.layout.xaxis.title, "text", None):
        ax.set_xlabel(str(fig.layout.xaxis.title.text), fontsize=10)
    if hasattr(fig.layout, "yaxis") and fig.layout.yaxis and getattr(fig.layout.yaxis.title, "text", None):
        ax.set_ylabel(str(fig.layout.yaxis.title.text), fontsize=10)

    if hasattr(ax, "get_legend_handles_labels") and ax.get_legend_handles_labels()[0]:
        ax.legend(loc="best", fontsize=8)

    # 7. Si no se pudo renderizar fielmente ningún tipo conocido, colocar aviso visible explícito
    if not has_rendered:
        ax.text(
            0.5, 0.5,
            "Aviso: Gráfico no compatible con conversión estática de alta fidelidad.\nDescargue la figura mediante el visor interactivo de Plotly en el navegador.",
            ha="center", va="center", color="#ef4444", fontsize=10, transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#fee2e2" if not is_dark else "#450a0a", edgecolor="#ef4444")
        )

    # Pie de procedencia metodológica en el margen inferior
    fig_mpl.text(
        0.99, 0.01,
        "Exportación estática (fallback Matplotlib · 600 DPI)",
        ha="right", va="bottom", fontsize=6, color="#888888" if not is_dark else "#6b7280", style="italic"
    )

    buf = io.BytesIO()
    fig_mpl.savefig(buf, format="png", dpi=600, bbox_inches="tight")
    plt.close(fig_mpl)
    buf.seek(0)
    return buf.getvalue()


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
            try:
                raw_png = fig.to_image(format="png", scale=4)
            except Exception:
                raw_png = _plotly_to_matplotlib_png(fig, width=w, height=h)
        im = Image.open(io.BytesIO(raw_png))
        im.save(buf, format="PNG", dpi=(600, 600))
        return buf.getvalue()
    elif hasattr(fig, "savefig"):
        # Figura Matplotlib
        fig.savefig(buf, format="png", dpi=600, bbox_inches="tight")
        im = Image.open(buf)
        buf2 = io.BytesIO()
        im.save(buf2, format="PNG", dpi=(600, 600))
        return buf2.getvalue()
    else:
        raise ValueError("El objeto de figura proporcionado no es compatible con Plotly ni con Matplotlib.")


def render_high_res_chart(fig: Any, filename: str, key_suffix: str = "") -> None:
    """Renderiza el gráfico Plotly en Streamlit configurado a 600 DPI
    y ofrece un botón para descargarlo directamente en ultra-alta resolución (600 DPI PNG con metadatos reales)."""
    clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", filename).strip("_") or "grafica"
    config = get_high_res_plotly_config(clean_name)
    st.plotly_chart(fig, use_container_width=True, config=config)

    btn_key = f"dl_png_{key_suffix}_{clean_name}"
    cache_key = f"_cache_png_{btn_key}"
    fp = (id(fig), clean_name, len(getattr(fig, "data", [])))

    session = getattr(st, "session_state", None)
    if session is not None and cache_key in session:
        cached_fp, cached_bytes = session[cache_key]
        if cached_fp == fp and isinstance(cached_bytes, (bytes, io.BytesIO)):
            img_bytes = cached_bytes
        else:
            img_bytes = export_figure_to_600dpi(fig)
            session[cache_key] = (fp, img_bytes)
    else:
        img_bytes = export_figure_to_600dpi(fig)
        if session is not None:
            session[cache_key] = (fp, img_bytes)

    st.download_button(
        label="📥 Descargar imagen en Alta Resolución (600 DPI PNG)",
        data=img_bytes,
        file_name=f"{clean_name}_600dpi.png",
        mime="image/png",
        key=btn_key,
        help="Descarga directa de esta figura en ultra-alta definición con metadatos de 600 DPI para publicación científica.",
    )
    st.caption("ℹ️ La descarga directa entrega un PNG estático a 600 DPI. Para la captura vectorial interactiva completa, use el botón de cámara de Plotly.")


def export_dataframe_to_excel(df: Any, sheet_name: str = "Datos", include_index: bool = False) -> bytes:
    """Convierte un DataFrame o Styler de pandas a archivo binario Excel (.xlsx) con openpyxl."""
    buf = io.BytesIO()
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


def _compute_dataframe_fingerprint(df: Any, sheet_name: str = "Datos", include_index: bool = False) -> tuple:
    """Calcula una huella digital determinista basada en el contenido real,
    índice, columnas, tipos de datos y parámetros de exportación del DataFrame o Styler.
    Detecta modificaciones in-place en celdas individuales sin alterar id(df), shape o columnas."""
    raw_df = df.data if hasattr(df, "data") else df

    if isinstance(raw_df, pd.DataFrame):
        try:
            # pd.util.hash_pandas_object calcula hashes por fila de forma vectorizada en C/NumPy
            row_hashes = pd.util.hash_pandas_object(raw_df, index=include_index).values
            content_hash = hashlib.sha256(row_hashes.tobytes()).hexdigest()
            cols = tuple(str(c) for c in raw_df.columns)
            dtypes = tuple(str(d) for d in raw_df.dtypes)
            idx_hash = ""
            if include_index:
                idx_hash = hashlib.sha256(str(list(raw_df.index)).encode("utf-8")).hexdigest()
            return (content_hash, cols, dtypes, idx_hash, str(sheet_name), bool(include_index))
        except Exception:
            pass

    # Fallback si no es DataFrame estándar
    try:
        content_repr = str(getattr(raw_df, "values", raw_df))
        content_hash = hashlib.sha256(content_repr.encode("utf-8")).hexdigest()
        return (content_hash, str(sheet_name), bool(include_index))
    except Exception:
        return (id(df), str(sheet_name), bool(include_index))


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
    para descargarla directamente en formato Microsoft Excel (.xlsx).
    
    Utiliza una huella de contenido exacta para detectar modificaciones in-place de valores
    y entrega datos binarios directos (bytes) compatibles con st.download_button."""
    df_kwargs: dict[str, Any] = {"use_container_width": use_container_width}
    if hide_index is not None:
        df_kwargs["hide_index"] = hide_index
    if column_config is not None:
        df_kwargs["column_config"] = column_config

    st.dataframe(df, **df_kwargs)

    clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", filename).strip("_") or "tabla"
    btn_key = f"dl_xlsx_{key_suffix}_{clean_name}"
    cache_key = f"_cache_excel_{btn_key}"

    # Huella basada en contenido real de celdas, índice, columnas y tipos
    fp = _compute_dataframe_fingerprint(df, sheet_name=sheet_name, include_index=include_index)

    session = getattr(st, "session_state", None)
    if session is not None and cache_key in session:
        cached_fp, cached_bytes = session[cache_key]
        if cached_fp == fp and isinstance(cached_bytes, (bytes, io.BytesIO)):
            excel_bytes = cached_bytes
        else:
            excel_bytes = export_dataframe_to_excel(df, sheet_name=sheet_name, include_index=include_index)
            session[cache_key] = (fp, excel_bytes)
    else:
        excel_bytes = export_dataframe_to_excel(df, sheet_name=sheet_name, include_index=include_index)
        if session is not None:
            session[cache_key] = (fp, excel_bytes)

    st.download_button(
        label="📥 Descargar tabla en Excel (.xlsx)",
        data=excel_bytes,
        file_name=f"{clean_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=btn_key,
        help=help_text or f"Descarga la tabla '{clean_name}' en formato Microsoft Excel (.xlsx).",
    )
