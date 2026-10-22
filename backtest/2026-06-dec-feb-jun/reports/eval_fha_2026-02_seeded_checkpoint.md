# Evaluation: fha_2026-02_SEEDED_checkpoint

- scored file: `final_predictions2026-07_fha_2026-02.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 169 | FP = 13800 |
| **Flagged No** | FN = 69 | TN = 19767 |

## Metrics

| metric | value |
|---|---|
| n_loans | 33805 |
| n_actual_refi | 238 |
| n_flagged | 13969 |
| pct_flagged | 0.41322289602129864 |
| recall | 0.7100840336134454 |
| precision | 0.012098217481566325 |
| legacy_specificity | 0.41322289602129864 |
| true_specificity_TN_over_TN_plus_FP | 0.5888819376173027 |
| auc | 0.6668948569686164 |
| ks | 0.27777080981646385 |