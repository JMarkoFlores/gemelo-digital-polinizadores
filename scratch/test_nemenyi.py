import numpy as np
import pandas as pd
from data_pipeline import generate_synthetic_dataset
from advanced_training import train_and_evaluate_all_models
from scipy import stats
import scikit_posthocs as sp

class MockText:
    def text(self, *args, **kwargs):
        pass

class MockProgress:
    def progress(self, *args, **kwargs):
        pass

def main():
    print("Generating dataset...")
    df = generate_synthetic_dataset(n_samples=320, random_state=42)
    print("Training models...")
    res = train_and_evaluate_all_models(df, MockProgress(), MockText())
    
    results_df = res['results_df']
    best = res['best_overall']
    print("Best model:", best)
    
    all_err = []
    models = results_df['Modelo'].tolist()
    for m in models:
        row = results_df[results_df['Modelo'] == m].iloc[0]
        y_true = row['last_y_true']
        y_pred = row['last_y_pred']
        abs_err = np.mean(np.abs(y_true - y_pred), axis=1)
        all_err.append(abs_err)
        
    stat_f, p_val_f = stats.friedmanchisquare(*all_err)
    print(f"Friedman p-val: {p_val_f}")
    
    if p_val_f < 0.05:
        data = np.array(all_err).T
        nemenyi = sp.posthoc_nemenyi_friedman(data)
        nemenyi.columns = models
        nemenyi.index = models
        print("Nemenyi p-values:")
        print(nemenyi)
        
        sig_pairs = []
        for i in range(len(models)):
            for j in range(i+1, len(models)):
                if nemenyi.iloc[i, j] < 0.05:
                    sig_pairs.append((models[i], models[j], nemenyi.iloc[i, j]))
        
        print("\nSignificant pairs:")
        for p in sig_pairs:
            print(f"{p[0]} vs {p[1]}: {p[2]}")
            
if __name__ == '__main__':
    main()
