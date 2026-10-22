# Evaluation: fha_2026-02_AFTER_F14_F22

- scored file: `final_predictions2026-07_fha_2026-02.csv`
- actuals files: ['PayoffReason2026-06.xlsx', 'PayoffReason2026-07.xlsx', 'PayoffReason2026-08.xlsx']

## Confusion matrix

|  | Actual refi | Actual no-refi |
|---|---|---|
| **Flagged Yes** | TP = 168 | FP = 13760 |
| **Flagged No** | FN = 70 | TN = 19807 |

## Metrics

| metric | value |
|---|---|
| n_loans | 33805 |
| n_actual_refi | 238 |
| n_flagged | 13928 |
| pct_flagged | 0.4120100576837746 |
| recall | 0.7058823529411765 |
| precision | 0.012062033314187249 |
| legacy_specificity | 0.4120100576837746 |
| true_specificity_TN_over_TN_plus_FP | 0.5900735841749337 |
| auc | 0.6579541907030039 |
| ks | 0.2643018240453747 |