# Evaluation: conventional_2026-05_SEEDED_checkpoint

- scored file: `final_predictions2026-07_conventional_2026-05.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 144 | FP = 22310 |
| **Flagged No** | FN = 79 | TN = 48845 |

## Metrics

| metric | value |
|---|---|
| n_loans | 71378 |
| n_actual_refi | 223 |
| n_flagged | 22454 |
| pct_flagged | 0.31457872173498835 |
| recall | 0.6457399103139013 |
| precision | 0.006413111249665984 |
| legacy_specificity | 0.31457872173498835 |
| true_specificity_TN_over_TN_plus_FP | 0.6864591385004567 |
| auc | 0.6495885789659599 |
| ks | 0.2349640288223177 |