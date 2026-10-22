# Evaluation: conventional_2026-02_AFTER_F14_F22

- scored file: `final_predictions2026-07_conventional_2026-02.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 144 | FP = 22365 |
| **Flagged No** | FN = 79 | TN = 48790 |

## Metrics

| metric | value |
|---|---|
| n_loans | 71378 |
| n_actual_refi | 223 |
| n_flagged | 22509 |
| pct_flagged | 0.31534926728123513 |
| recall | 0.6457399103139013 |
| precision | 0.006397441023590564 |
| legacy_specificity | 0.31534926728123513 |
| true_specificity_TN_over_TN_plus_FP | 0.6856861780619774 |
| auc | 0.6097055219247566 |
| ks | 0.19542973354764892 |