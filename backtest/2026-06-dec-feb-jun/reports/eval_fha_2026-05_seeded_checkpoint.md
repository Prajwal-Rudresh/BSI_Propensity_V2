# Evaluation: fha_2026-05_SEEDED_checkpoint

- scored file: `final_predictions2026-07_fha_2026-05.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 169 | FP = 13404 |
| **Flagged No** | FN = 69 | TN = 20163 |

## Metrics

| metric | value |
|---|---|
| n_loans | 33805 |
| n_actual_refi | 238 |
| n_flagged | 13573 |
| pct_flagged | 0.40150865256618845 |
| recall | 0.7100840336134454 |
| precision | 0.012451189862226479 |
| legacy_specificity | 0.40150865256618845 |
| true_specificity_TN_over_TN_plus_FP | 0.6006792385378497 |
| auc | 0.7304546807551334 |
| ks | 0.3637257029901066 |