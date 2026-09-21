from __future__ import annotations

import base64
import io
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _fig_to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def render_operational_trend_chart(tendencia: list[dict[str, Any]]) -> str:
    """Genera gráfica de tendencia temporal de simulaciones (periodo y acumulado)."""
    if not tendencia:
        fig, ax = plt.subplots(figsize=(8, 3.2))
        ax.text(0.5, 0.5, "Sin datos de simulaciones en el periodo", ha="center", va="center", color="#64748b")
        ax.axis("off")
        return _fig_to_base64(fig)

    periodos = [str(item.get("periodo", "")) for item in tendencia]
    simulaciones = [int(item.get("simulaciones", 0)) for item in tendencia]
    acumulado = [int(item.get("acumulado", 0)) for item in tendencia]

    fig, ax1 = plt.subplots(figsize=(8.5, 3.6))
    fig.patch.set_facecolor("white")
    ax1.set_facecolor("#fafafa")

    # Bar chart for per-period simulations
    x = np.arange(len(periodos))
    bars = ax1.bar(x, simulaciones, width=0.45, color="#10b981", alpha=0.85, label="Simulaciones por Periodo")

    ax1.set_xlabel("Periodo / Fecha", fontsize=9, fontweight="bold", color="#334155", labelpad=8)
    ax1.set_ylabel("Simulaciones", fontsize=9, fontweight="bold", color="#10b981", labelpad=8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(periodos, rotation=35, ha="right", fontsize=8, color="#475569")
    ax1.grid(axis="y", linestyle="--", alpha=0.5, color="#cbd5e1")
    ax1.tick_params(axis="y", colors="#10b981", labelsize=8)

    # Line chart for cumulative simulations on secondary y-axis
    ax2 = ax1.twinx()
    line = ax2.plot(x, acumulado, color="#0284c7", linewidth=2.4, marker="o", markersize=4.5, label="Total Acumulado")
    ax2.set_ylabel("Acumulado", fontsize=9, fontweight="bold", color="#0284c7", labelpad=8)
    ax2.tick_params(axis="y", colors="#0284c7", labelsize=8)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=True, facecolor="white", edgecolor="#e2e8f0", fontsize=8)

    ax1.set_title("Tendencia de Uso de la Plataforma (Simulaciones)", fontsize=11, fontweight="bold", color="#0f172a", pad=12)

    return _fig_to_base64(fig)


def render_operational_regions_chart(regiones: list[dict[str, Any]]) -> str:
    """Genera gráfica de barras horizontal con la distribución de regiones más simuladas."""
    if not regiones:
        fig, ax = plt.subplots(figsize=(8, 3.2))
        ax.text(0.5, 0.5, "Sin regiones registradas", ha="center", va="center", color="#64748b")
        ax.axis("off")
        return _fig_to_base64(fig)

    sorted_regiones = sorted(regiones, key=lambda r: r.get("total", 0), reverse=True)[:8]
    names = [str(r.get("region", "Sin definir")) for r in sorted_regiones][::-1]
    totals = [int(r.get("total", 0)) for r in sorted_regiones][::-1]

    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fafafa")

    y_pos = np.arange(len(names))
    bars = ax.barh(y_pos, totals, height=0.55, color="#059669", alpha=0.85)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=8.5, color="#334155")
    ax.set_xlabel("Número de Simulaciones", fontsize=9, fontweight="bold", color="#334155", labelpad=8)
    ax.grid(axis="x", linestyle="--", alpha=0.5, color="#cbd5e1")
    ax.tick_params(axis="x", colors="#475569", labelsize=8)

    for bar in bars:
        width = bar.get_width()
        ax.annotate(f"{width}",
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(4, 0),
                    textcoords="offset points",
                    ha="left", va="center", fontsize=8, color="#0f172a", fontweight="bold")

    ax.set_title("Distribución de Simulaciones por Región Agroecológica", fontsize=11, fontweight="bold", color="#0f172a", pad=12)

    return _fig_to_base64(fig)


def render_management_evolution_chart(evolucion: list[dict[str, Any]]) -> str:
    """Genera gráfica de líneas con la evolución agroecológica (Rendimiento y Polinizadores)."""
    if not evolucion:
        fig, ax = plt.subplots(figsize=(8.5, 3.6))
        ax.text(0.5, 0.5, "Sin datos de evolución agroecológica", ha="center", va="center", color="#64748b")
        ax.axis("off")
        return _fig_to_base64(fig)

    fechas = [str(e.get("fecha", "")) for e in evolucion]
    y_opt = [float(e.get("rendimiento_optimo", 0)) for e in evolucion]
    y_base = [float(e.get("rendimiento_base", 0)) for e in evolucion]
    p_opt = [float(e.get("abundancia_optima", 0)) for e in evolucion]
    p_base = [float(e.get("abundancia_base", 0)) for e in evolucion]

    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fafafa")

    x = np.arange(len(fechas))

    ax.plot(x, y_opt, label="Rendimiento Óptimo", color="#10b981", linewidth=2.4, marker="o", markersize=4)
    ax.plot(x, y_base, label="Rendimiento Base", color="#94a3b8", linestyle="--", linewidth=1.8)
    ax.plot(x, p_opt, label="Abundancia Polinizadores (Ópt.)", color="#f59e0b", linewidth=2.4, marker="s", markersize=4)
    ax.plot(x, p_base, label="Abundancia Polinizadores (Base)", color="#fcd34d", linestyle="--", linewidth=1.8)

    ax.set_xlabel("Fecha de Simulación", fontsize=9, fontweight="bold", color="#334155", labelpad=8)
    ax.set_ylabel("Índice / Puntos", fontsize=9, fontweight="bold", color="#334155", labelpad=8)
    ax.set_xticks(x)
    ax.set_xticklabels(fechas, rotation=35, ha="right", fontsize=8, color="#475569")
    ax.grid(axis="both", linestyle="--", alpha=0.5, color="#cbd5e1")
    ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#e2e8f0", fontsize=8)
    ax.set_title("Evolución Agroecológica en el Tiempo (Base vs. Óptimo)", fontsize=11, fontweight="bold", color="#0f172a", pad=12)

    return _fig_to_base64(fig)


def render_management_regional_chart(regiones: list[dict[str, Any]]) -> str:
    """Genera gráfica de barras agrupadas comparando Rendimiento, Polinizadores e Hipótesis por región."""
    if not regiones:
        fig, ax = plt.subplots(figsize=(8.5, 3.6))
        ax.text(0.5, 0.5, "Sin datos de regiones para comparación", ha="center", va="center", color="#64748b")
        ax.axis("off")
        return _fig_to_base64(fig)

    sorted_regs = regiones[:7]
    names = [str(r.get("region", "N/D")) for r in sorted_regs]
    rendimiento = [float(r.get("rendimiento_promedio_optimo", 0)) for r in sorted_regs]
    polinizadores = [float(r.get("abundancia_promedio_optimo", 0)) for r in sorted_regs]
    hipotesis = [float(r.get("tasa_cumplimiento_hipotesis", 0)) for r in sorted_regs]

    x = np.arange(len(names))
    width = 0.25

    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fafafa")

    ax.bar(x - width, rendimiento, width, label="Rendimiento Óptimo", color="#10b981", alpha=0.9)
    ax.bar(x, polinizadores, width, label="Abundancia Polinizadores", color="#f59e0b", alpha=0.9)
    ax.bar(x + width, hipotesis, width, label="% Hipótesis Comprobada", color="#0284c7", alpha=0.9)

    ax.set_xlabel("Región Agroecológica", fontsize=9, fontweight="bold", color="#334155", labelpad=8)
    ax.set_ylabel("Valor / Porcentaje (%)", fontsize=9, fontweight="bold", color="#334155", labelpad=8)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=25, ha="right", fontsize=8, color="#475569")
    ax.grid(axis="y", linestyle="--", alpha=0.5, color="#cbd5e1")
    ax.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#e2e8f0", fontsize=8)
    ax.set_title("Comparativa Multiobjetivo por Región Agroecológica", fontsize=11, fontweight="bold", color="#0f172a", pad=12)

    return _fig_to_base64(fig)
