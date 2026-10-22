# Evaluation: fha_2026-05_AFTER_F14_F22

- scored file: `final_predictions2026-07_fha_2026-05.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 169 | FP = 13520 |
| **Flagged No** | FN = 69 | TN = 20047 |

## Metrics

| metric | value |
|---|---|
| n_loans | 33805 |
| n_actual_refi | 238 |
| n_flagged | 13689 |
| pct_flagged | 0.4049400976186955 |
| recall | 0.7100840336134454 |
| precision | 0.012345679012345678 |
| legacy_specificity | 0.4049400976186955 |
| true_specificity_TN_over_TN_plus_FP | 0.5972234635207198 |
| auc | 0.7277281633897638 |
| ks | 0.36436032988581973 |