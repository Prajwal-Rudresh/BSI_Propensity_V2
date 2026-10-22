# Evaluation: fha_2026-02_AFTER_F5

- scored file: `final_predictions2026-07_fha_2026-02.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 169 | FP = 13962 |
| **Flagged No** | FN = 69 | TN = 19605 |

## Metrics

| metric | value |
|---|---|
| n_loans | 33805 |
| n_actual_refi | 238 |
| n_flagged | 14131 |
| pct_flagged | 0.4180150865256619 |
| recall | 0.7100840336134454 |
| precision | 0.011959521619135235 |
| legacy_specificity | 0.4180150865256619 |
| true_specificity_TN_over_TN_plus_FP | 0.5840557690588971 |
| auc | 0.6831869310419673 |
| ks | 0.32652154614638773 |