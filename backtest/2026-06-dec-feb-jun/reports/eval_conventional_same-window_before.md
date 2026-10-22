# Evaluation: conventional_same-window_BEFORE

- scored file: `final_predictions2026-07_conventional_2026-02.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 144 | FP = 22223 |
| **Flagged No** | FN = 79 | TN = 48932 |

## Metrics

| metric | value |
|---|---|
| n_loans | 71378 |
| n_actual_refi | 223 |
| n_flagged | 22367 |
| pct_flagged | 0.31335985878001626 |
| recall | 0.6457399103139013 |
| precision | 0.0064380560647382306 |
| legacy_specificity | 0.31335985878001626 |
| true_specificity_TN_over_TN_plus_FP | 0.6876818213758695 |
| auc | 0.6493363663548881 |
| ks | 0.22949646023192594 |