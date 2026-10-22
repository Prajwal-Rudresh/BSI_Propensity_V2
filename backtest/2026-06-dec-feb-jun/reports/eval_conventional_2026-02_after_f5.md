# Evaluation: conventional_2026-02_AFTER_F5

- scored file: `final_predictions2026-07_conventional_2026-02.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 144 | FP = 22368 |
| **Flagged No** | FN = 79 | TN = 48787 |

## Metrics

| metric | value |
|---|---|
| n_loans | 71378 |
| n_actual_refi | 223 |
| n_flagged | 22512 |
| pct_flagged | 0.3153912970383031 |
| recall | 0.6457399103139013 |
| precision | 0.006396588486140725 |
| legacy_specificity | 0.3153912970383031 |
| true_specificity_TN_over_TN_plus_FP | 0.6856440165835148 |
| auc | 0.6149802758016116 |
| ks | 0.1919370741509488 |