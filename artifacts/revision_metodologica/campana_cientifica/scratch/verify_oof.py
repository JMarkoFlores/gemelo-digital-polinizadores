import pandas as pd
import numpy as np

oof_path = 'artifacts/revision_metodologica/campana_cientifica/run_20261029_153857/oof_predictions.csv'
oof = pd.read_csv(oof_path)
print('Total OOF rows:', len(oof))
expected_rows = 5 * 3 * 320
print('Expected OOF rows:', expected_rows, 'Match:', len(oof) == expected_rows)

dups = oof.duplicated(subset=['sample_id', 'target', 'model_id']).sum()
print('Duplicate tuples (sample_id, target, model_id):', dups)

models = sorted(oof['model_id'].unique())
targets = sorted(oof['target'].unique())
print('Models:', models)
print('Targets:', targets)

all_covered = True
for m in models:
    for t in targets:
        sub = oof[(oof['model_id'] == m) & (oof['target'] == t)]
        if len(sub) != 320:
            print(f'Missing rows for model {m}, target {t}: {len(sub)}')
            all_covered = False
        if sub['sample_id'].nunique() != 320:
            print(f'Missing sample_ids for model {m}, target {t}: {sub["sample_id"].nunique()}')
            all_covered = False
print('All 320 sample_ids covered for all models and targets:', all_covered)

print('NaNs in y_true:', int(oof['y_true'].isna().sum()))
print('NaNs in y_pred:', int(oof['y_pred'].isna().sum()))
print('Infs in y_pred:', int(np.isinf(oof['y_pred']).sum()))
