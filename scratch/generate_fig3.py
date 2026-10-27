import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import json
import requests
from PIL import Image

def generate_figure_3():
    # 1. Fetch simulation 4 data from deployed API
    base_url = "https://gemelo-agro.duckdns.org/api"
    login_data = {"email": "jeanmpachecof@gmail.com", "password": "jeanmarko"}

    r = requests.post(f"{base_url}/api/auth/login", json=login_data, verify=False)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(f"{base_url}/api/simulations/me/4", headers=headers, verify=False)
    sim_data = res.json()
    pareto = sim_data.get("frente_pareto", [])
    base_m = sim_data.get("metricas_base", {})
    opt_m = sim_data.get("metricas_optimas", {})

    print(f"Loaded {len(pareto)} pareto alternatives from deployed system.")

    # Extract pareto points
    yields = [p["crop_yield_index"] for p in pareto]
    abundances = [p["pollinator_abundance_index"] for p in pareto]

    base_yield = base_m.get("crop_yield_index", 92.218)
    base_abund = base_m.get("pollinator_abundance_index", 87.954)

    opt_yield = opt_m.get("crop_yield_index", 97.500)
    opt_abund = opt_m.get("pollinator_abundance_index", 135.091)

    # Land use percentages
    cov_labels = ['Cultivo', 'Área natural', 'Cobertura floral']
    base_cov = [base_m.get("crop_area_pct", 74.40), base_m.get("natural_area_pct", 20.00), base_m.get("floral_strips_pct", 5.60)]
    opt_cov = [opt_m.get("crop_area_pct", 35.01), opt_m.get("natural_area_pct", 45.00), opt_m.get("floral_strips_pct", 19.99)]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), dpi=600)
    fig.patch.set_facecolor('white')

    # ─────────────────────────────────────────────────────────────────────────
    # PANEL (a): FRENTE DE PARETO (Soluciones de optimización NSGA-II)
    # ─────────────────────────────────────────────────────────────────────────
    ax_a = axes[0]
    ax_a.set_facecolor('#ffffff')

    # Scatter 64 Pareto candidates
    ax_a.scatter(
        yields, abundances,
        color='#94a3b8', edgecolor='#475569', s=70, alpha=0.85, zorder=3,
        label='Alternativas NSGA-II (n=64)'
    )

    # Plot baseline
    ax_a.scatter(
        [base_yield], [base_abund],
        color='#e11d48', edgecolor='#881337', s=160, marker='D', zorder=5,
        label=f'Línea base heurística ({base_yield:.1f}, {base_abund:.1f})'
    )

    # Plot selected / optimal solution
    ax_a.scatter(
        [opt_yield], [opt_abund],
        color='#059669', edgecolor='#064e3b', s=240, marker='*', zorder=6,
        label=f'Solución seleccionada ({opt_yield:.1f}, {opt_abund:.1f})'
    )

    # Annotate baseline
    ax_a.annotate(
        f'Línea base\n({base_yield:.2f}; {base_abund:.2f})',
        xy=(base_yield, base_abund),
        xytext=(base_yield + 1.2, base_abund - 8.0),
        fontsize=8.5, fontweight='bold', color='#9f1239',
        arrowprops=dict(arrowstyle='->', color='#e11d48', lw=1.2),
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#fff1f2', edgecolor='#fecdd3', alpha=0.95)
    )

    # Annotate optimal solution
    ax_a.annotate(
        f'Solución seleccionada\n(+5.28 pts rend; +53.59% ab)\n({opt_yield:.2f}; {opt_abund:.2f})',
        xy=(opt_yield, opt_abund),
        xytext=(opt_yield + 1.5, opt_abund - 6.0),
        fontsize=8.5, fontweight='bold', color='#065f46',
        arrowprops=dict(arrowstyle='->', color='#059669', lw=1.2),
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#ecfdf5', edgecolor='#a7f3d0', alpha=0.95)
    )

    ax_a.set_xlabel('Índice predicho de rendimiento agrícola', fontsize=9.5, fontweight='bold', color='#334155', labelpad=8)
    ax_a.set_ylabel('Índice predicho de abundancia de polinizadores', fontsize=9.5, fontweight='bold', color='#334155', labelpad=8)
    ax_a.set_title('(a) Compromisos multiobjetivo y soluciones NSGA-II', fontsize=11, fontweight='bold', color='#0f172a', pad=10)
    ax_a.grid(True, linestyle='--', alpha=0.45, color='#cbd5e1')
    ax_a.set_axisbelow(True)
    ax_a.legend(loc='lower left', frameon=True, facecolor='white', edgecolor='#e2e8f0', fontsize=8.5)

    # ─────────────────────────────────────────────────────────────────────────
    # PANEL (b): COMPOSICIÓN DE COBERTURAS (% DEL PAISAJE)
    # ─────────────────────────────────────────────────────────────────────────
    ax_b = axes[1]
    ax_b.set_facecolor('#ffffff')

    x_indices = np.arange(len(cov_labels))
    bar_width = 0.35

    color_initial = '#d97706'    # Amber for initial
    color_opt = '#2563eb'        # Royal blue for selected

    bars_init = ax_b.bar(
        x_indices - bar_width/2, base_cov, width=bar_width,
        color=color_initial, edgecolor='none', label='Configuración inicial (Línea base)', zorder=3
    )
    bars_rec = ax_b.bar(
        x_indices + bar_width/2, opt_cov, width=bar_width,
        color=color_opt, edgecolor='none', label='Configuración seleccionada (Recomendada)', zorder=3
    )

    ax_b.set_xticks(x_indices)
    ax_b.set_xticklabels(cov_labels, fontsize=9.5, fontweight='bold', color='#1e293b')
    ax_b.set_ylabel('Proporción del paisaje (%)', fontsize=9.5, fontweight='bold', color='#334155', labelpad=8)
    ax_b.set_title('(b) Composición porcentual de coberturas del suelo', fontsize=11, fontweight='bold', color='#0f172a', pad=10)
    ax_b.set_ylim(0, 90)
    ax_b.grid(axis='y', linestyle='--', alpha=0.45, color='#cbd5e1')
    ax_b.set_axisbelow(True)
    ax_b.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='#e2e8f0', fontsize=8.5)

    # Value labels on bars
    for bar in bars_init:
        h = bar.get_height()
        ax_b.text(bar.get_x() + bar.get_width()/2, h + 1.2, f"{h:.2f}%",
                  ha='center', va='bottom', fontsize=8.5, fontweight='bold', color=color_initial)

    for bar in bars_rec:
        h = bar.get_height()
        ax_b.text(bar.get_x() + bar.get_width()/2, h + 1.2, f"{h:.2f}%",
                  ha='center', va='bottom', fontsize=8.5, fontweight='bold', color=color_opt)

    for ax in [ax_a, ax_b]:
        ax.tick_params(colors='#475569', labelsize=8.5)
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        ax.spines['left'].set_color('#94a3b8')
        ax.spines['bottom'].set_color('#94a3b8')

    plt.tight_layout(pad=2.2)
    out_path = 'scratch/figura3_600dpi.png'
    fig.savefig(out_path, dpi=600, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)

    im = Image.open(out_path)
    print("Figura 3 generated:", im.size, "DPI:", im.info.get('dpi'))
    return out_path

generate_figure_3()
