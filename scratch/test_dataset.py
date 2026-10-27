import sys
sys.path.append('streamlit_app')
import numpy as np
import pandas as pd
from data_pipeline import generate_synthetic_dataset, build_real_public_dataset

df_synth, meta_synth = generate_synthetic_dataset(n_samples=320, random_state=42)
print("Synthetic dataset shape:", df_synth.shape)
print("Synthetic columns:", df_synth.columns.tolist())
print(df_synth.describe().round(2))
