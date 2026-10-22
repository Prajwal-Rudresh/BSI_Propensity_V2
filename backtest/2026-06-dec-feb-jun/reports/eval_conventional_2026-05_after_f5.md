# Evaluation: conventional_2026-05_AFTER_F5

- scored file: `final_predictions2026-07_conventional_2026-05.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 144 | FP = 22369 |
| **Flagged No** | FN = 79 | TN = 48786 |

## Metrics

| metric | value |
|---|---|
| n_loans | 71378 |
| n_actual_refi | 223 |
| n_flagged | 22513 |
| pct_flagged | 0.31540530695732577 |
| recall | 0.6457399103139013 |
| precision | 0.006396304357482343 |
| legacy_specificity | 0.31540530695732577 |
| true_specificity_TN_over_TN_plus_FP | 0.6856299627573607 |
| auc | 0.6324840011684213 |
| ks | 0.2048036355924806 |