# Evaluation: conventional_2026-05_AFTER_F14_F22

- scored file: `final_predictions2026-07_conventional_2026-05.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 142 | FP = 21480 |
| **Flagged No** | FN = 81 | TN = 49675 |

## Metrics

| metric | value |
|---|---|
| n_loans | 71378 |
| n_actual_refi | 223 |
| n_flagged | 21622 |
| pct_flagged | 0.30292246910812853 |
| recall | 0.6367713004484304 |
| precision | 0.006567385070761262 |
| legacy_specificity | 0.30292246910812853 |
| true_specificity_TN_over_TN_plus_FP | 0.6981238142084183 |
| auc | 0.6445800915263307 |
| ks | 0.21345392314447742 |