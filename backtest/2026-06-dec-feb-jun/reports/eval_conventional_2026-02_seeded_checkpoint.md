# Evaluation: conventional_2026-02_SEEDED_checkpoint

- scored file: `final_predictions2026-07_conventional_2026-02.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 143 | FP = 21921 |
| **Flagged No** | FN = 80 | TN = 49234 |

## Metrics

| metric | value |
|---|---|
| n_loans | 71378 |
| n_actual_refi | 223 |
| n_flagged | 22064 |
| pct_flagged | 0.30911485331614785 |
| recall | 0.6412556053811659 |
| precision | 0.006481145757795504 |
| legacy_specificity | 0.30911485331614785 |
| true_specificity_TN_over_TN_plus_FP | 0.6919260768744291 |
| auc | 0.6567039114066966 |
| ks | 0.23941612969601828 |