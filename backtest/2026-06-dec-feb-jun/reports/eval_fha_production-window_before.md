# Evaluation: fha_production-window_BEFORE

- scored file: `final_predictions2026-07_fha_2026-05.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 168 | FP = 13600 |
| **Flagged No** | FN = 70 | TN = 19967 |

## Metrics

| metric | value |
|---|---|
| n_loans | 33805 |
| n_actual_refi | 238 |
| n_flagged | 13768 |
| pct_flagged | 0.4072770300251442 |
| recall | 0.7058823529411765 |
| precision | 0.01220220801859384 |
| legacy_specificity | 0.4072770300251442 |
| true_specificity_TN_over_TN_plus_FP | 0.5948401704054578 |
| auc | 0.7343930601108082 |
| ks | 0.3495665135300702 |