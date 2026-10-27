import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io
import json
import requests
from PIL import Image

# 1. GENERATE FIGURE 2 (600 DPI)
def generate_figure_2():
    # Model evaluation metrics from Tabla 3
    models = ['Regresión Ridge', 'DNN', 'Autoencoder+MLP', 'Random Forest', 'XGBoost']
    mae = [6.2429, 6.2126, 6.3104, 6.3952, 6.9295]
    rmse = [7.2511, 7.3354, 7.4420, 7.6569, 8.1605]
    r2 = [0.4778, 0.4712, 0.4568, 0.4352, 0.3838]

    # Best values:
    # MAE: min (DNN: 6.2126)
    # RMSE: min (Ridge: 7.2511)
    # R2: max (Ridge: 0.4778)
    
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.2), dpi=600)
    fig.patch.set_facecolor('white')

    bar_color_default = '#1e3a8a'  # Classic deep navy
    bar_color_best = '#059669'     # Crisp academic emerald green

    # Panel (a) MAE
    colors_mae = [bar_color_best if val == min(mae) else bar_color_default for val in mae]
    y_pos = np.arange(len(models))
    bars_mae = axes[0].barh(y_pos, mae, color=colors_mae, height=0.62, edgecolor='none')
    axes[0].set_yticks(y_pos)
    axes[0].set_yticklabels(models, fontsize=9.5, fontweight='medium', color='#1e293b')
    axes[0].invert_yaxis()  # Top-down
    axes[0].set_xlim(0, 8.2)
    axes[0].set_xlabel('MAE (unidades originales)', fontsize=9.5, fontweight='bold', color='#334155', labelpad=8)
    axes[0].set_title('(a) MAE', fontsize=11, fontweight='bold', color='#0f172a', pad=10)
    axes[0].grid(axis='x', linestyle='--', alpha=0.45, color='#cbd5e1')
    axes[0].set_axisbelow(True)
    for bar in bars_mae:
        w = bar.get_width()
        axes[0].text(w + 0.12, bar.get_y() + bar.get_height()/2, f"{w:.4f}", 
                     va='center', ha='left', fontsize=8.5, fontweight='semibold', color='#1e293b')

    # Panel (b) RMSE
    colors_rmse = [bar_color_best if val == min(rmse) else bar_color_default for val in rmse]
    bars_rmse = axes[1].barh(y_pos, rmse, color=colors_rmse, height=0.62, edgecolor='none')
    axes[1].set_yticks(y_pos)
    axes[1].set_yticklabels([])  # Hide duplicate model labels
    axes[1].invert_yaxis()
    axes[1].set_xlim(0, 9.6)
    axes[1].set_xlabel('RMSE (unidades originales)', fontsize=9.5, fontweight='bold', color='#334155', labelpad=8)
    axes[1].set_title('(b) RMSE', fontsize=11, fontweight='bold', color='#0f172a', pad=10)
    axes[1].grid(axis='x', linestyle='--', alpha=0.45, color='#cbd5e1')
    axes[1].set_axisbelow(True)
    for bar in bars_rmse:
        w = bar.get_width()
        axes[1].text(w + 0.14, bar.get_y() + bar.get_height()/2, f"{w:.4f}", 
                     va='center', ha='left', fontsize=8.5, fontweight='semibold', color='#1e293b')

    # Panel (c) R2
    colors_r2 = [bar_color_best if val == max(r2) else bar_color_default for val in r2]
    bars_r2 = axes[2].barh(y_pos, r2, color=colors_r2, height=0.62, edgecolor='none')
    axes[2].set_yticks(y_pos)
    axes[2].set_yticklabels([])  # Hide duplicate model labels
    axes[2].invert_yaxis()
    axes[2].set_xlim(0, 0.62)
    axes[2].set_xlabel(r'$R^2$ (adimensional)', fontsize=9.5, fontweight='bold', color='#334155', labelpad=8)
    axes[2].set_title(r'(c) $R^2$', fontsize=11, fontweight='bold', color='#0f172a', pad=10)
    axes[2].grid(axis='x', linestyle='--', alpha=0.45, color='#cbd5e1')
    axes[2].set_axisbelow(True)
    for bar in bars_r2:
        w = bar.get_width()
        axes[2].text(w + 0.012, bar.get_y() + bar.get_height()/2, f"{w:.4f}", 
                     va='center', ha='left', fontsize=8.5, fontweight='semibold', color='#1e293b')

    for ax in axes:
        ax.tick_params(colors='#475569', labelsize=8.5)
        for spine in ['top', 'right', 'left']:
            ax.spines[spine].set_visible(False)
        ax.spines['bottom'].set_color('#94a3b8')

    plt.tight_layout(pad=2.0)
    out_path = 'scratch/figura2_600dpi.png'
    fig.savefig(out_path, dpi=600, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    
    # Verify DPI with PIL
    im = Image.open(out_path)
    print("Figura 2 generated:", im.size, "DPI:", im.info.get('dpi'))
    return out_path

generate_figure_2()
