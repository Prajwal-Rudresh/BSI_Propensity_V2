# Evaluation: fha_same-window_BEFORE

- scored file: `final_predictions2026-07_fha_2026-02.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 170 | FP = 13882 |
| **Flagged No** | FN = 68 | TN = 19685 |

## Metrics

| metric | value |
|---|---|
| n_loans | 33805 |
| n_actual_refi | 238 |
| n_flagged | 14052 |
| pct_flagged | 0.41567815411921316 |
| recall | 0.7142857142857143 |
| precision | 0.012097922003985198 |
| legacy_specificity | 0.41567815411921316 |
| true_specificity_TN_over_TN_plus_FP | 0.5864390621741592 |
| auc | 0.676431471686002 |
| ks | 0.2901740730254029 |