# Evaluation: fha_2026-05_AFTER_F5

- scored file: `final_predictions2026-07_fha_2026-05.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 169 | FP = 13567 |
| **Flagged No** | FN = 69 | TN = 20000 |

## Metrics

| metric | value |
|---|---|
| n_loans | 33805 |
| n_actual_refi | 238 |
| n_flagged | 13736 |
| pct_flagged | 0.4063304244934181 |
| recall | 0.7100840336134454 |
| precision | 0.01230343622597554 |
| legacy_specificity | 0.4063304244934181 |
| true_specificity_TN_over_TN_plus_FP | 0.5958232788155033 |
| auc | 0.7258118905798085 |
| ks | 0.345401258188502 |