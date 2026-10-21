# Scope and Change Policy

## Scope

### In scope — normal review, no score change
- Add **Precision, AUC, KS, % flagged** to the report as new columns. Existing metrics unchanged.
- **Keep the existing Specificity formula.** Document what it measures; do not change it.
- Replace hardcoded dates/paths with values derived from run month + config.
- Versioned model artifacts (`{universe}/{YYYY-MM}/model.pkl` + run manifest). No manual renaming.
- Data-contract checks (layout, row counts ±10%, unique loan numbers, join match rate, null-rate
  limits, constant columns, rate freshness) — they **warn or halt**, they never alter data.
- Logging, config, type hints, error handling, modular structure, tests, CI, docs, runbook.
- Security: secrets out of code, parameterized SQL, no data in the repo.

### Needs sign-off — changes delivered scores or model inputs
- F1 `pred_prob` / `y_pred` mismatch fix
- F5 `Flag_Trailing_DaysDiff_GT45` definition fix
- F6 `Login_Count` join fix (if the join is broken)
- F7 duplicate "Loan Number" / join-key fix (if it affects joins)

### Out of scope — do not implement
- New features, feature removal, re-selection
- Threshold / cutoff changes, deciles, ranking output
- Probability calibration
- New algorithms (XGBoost, LightGBM, etc.) or hyperparameter changes
- Changing the 12-month window or WoE binning approach
- Switching the market-rate source (separate ADR-001)

## Change types

| Type | Definition | Golden master | Process |
|---|---|---|---|
| **Code change** | Behavior identical | Unchanged | PR + review + green CI |
| **Additive output** | New columns/metrics only; existing values identical | Unchanged for existing columns | PR + review + green CI |
| **Model/score change** | Any delivered score, flag or model input changes | Changes | Branch → before/after diff on Aug 2026 + Jul 2025 backtest → Anwar sign-off → separate PR that updates golden master → version bump + CHANGELOG |

## Before/after diff (required for sign-off changes)

Report, per universe:
- Loans whose `y_pred` changed (count, %, Yes→No and No→Yes)
- Distribution of `pred_prob` change (min / median / max)
- Metrics before vs. after (Recall, existing Specificity, Precision, AUC, KS, % flagged)
- Root cause in one paragraph, with file and line
- Aggregates only — no loan-level data in the PR or repo

## Versioning

- `v0-flowise-original` — untouched legacy export
- `v1.0.0` — Python pipeline reproducing Aug 2026 exactly (parity)
- Minor bump (`v1.1.0`) for additive outputs; major bump for any signed-off score change
- Every release has a CHANGELOG entry and the golden-master status

## People

- **Anwar** — PG process owner; approver for any score change and for monthly delivery
- **Prajwal** — author / maintainer of this repo
- **Data engineering** — owners of the Asset360 SQL pulls and scheduling
- **IT / security** — approvals for tooling, GitHub hosting, self-hosted runners
