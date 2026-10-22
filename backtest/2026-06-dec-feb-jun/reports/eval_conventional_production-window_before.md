# Evaluation: conventional_production-window_BEFORE

- scored file: `final_predictions2026-07_conventional_2026-05.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 143 | FP = 21688 |
| **Flagged No** | FN = 80 | TN = 49467 |

## Metrics

| metric | value |
|---|---|
| n_loans | 71378 |
| n_actual_refi | 223 |
| n_flagged | 21831 |
| pct_flagged | 0.3058505421838662 |
| recall | 0.6412556053811659 |
| precision | 0.0065503183546333195 |
| legacy_specificity | 0.3058505421838662 |
| true_specificity_TN_over_TN_plus_FP | 0.6952006183683508 |
| auc | 0.6293788618480529 |
| ks | 0.1963143683356583 |