# Backtest Plan: Base Model, Dec 2025–Feb 2026 Train / June 2026 Test

Formalized from `backtest-handoff.md` (received 2026-10-21, originally a standalone handoff doc).
This describes a separate track from the Phase 3 golden-master parity work
(`project-background.md`'s Aug 2026 target): a backtest of the **base (legacy) model** against a
later window, and the groundwork for comparing it to a future improved model. Per
`scope-and-change-policy.md`, any improved-model work stays on its own branch/folder and is never
delivered without Anwar's sign-off.

## Rules (always apply — restates CLAUDE.md hard rules for this track)

- Use synthetic data only in prompts, code, tests, docs. Never put real borrower data in any of
  those. Real files for this backtest live in `data/real/` (git-ignored) — see
  `data/real/MANIFEST.md`.
- Don't change model behavior without sign-off from Anwar, the process owner.
- Keep the legacy "Specificity" formula as-is. It equals the % of loans flagged.
- New metrics are additive only.
- Never edit golden-master files.
- Don't guess. When something is ambiguous, list the options.
- The improved model stays on its own branch or folder and is never delivered without sign-off.

## Production path (now at repo root, not `legacy/` — see `CLAUDE.md` repo layout)

`modeling_data/run.py` → `data_preperation/TrainingDataPreperation_new_features.py` →
`Modeling/modelTraining.py` (FHA) or `modelTraining_conventional.py` →
`Modeling/PredictionDataPreperation.py` → `Modeling/ModelInference.py`

- The model is LightGBM, trained with SMOTE and tuned with Optuna.
- Yes/No flags use a 0.025 cutoff plus 3 override rules (`ModelInference.py:271-282`, see F12).
- The model runs separately for two universes:
  - **Conventional:** Conventional + PMI
  - **FHA:** FHA + VA

## Experiment design

| Item | Value |
|---|---|
| Train snapshots | Dec 2025, Jan 2026, Feb 2026 |
| Training labels | Payoffs Dec 2025 → May 2026 |
| Test snapshot | June 2026 |
| Test actuals | Refi payoffs in June, July and August 2026 |
| Tool settings | start `2025-11` (excluded, `BuildFeatures_new_features.py:73`), end `2026-02`, test `2026-06` |
| Leakage rule | The last training month + 3 months must be before the test month |

**Two base-model baselines:**

1. **Production setting:** a 12-month window ending the month before the test.
2. **Same window as the improved model:** Dec 2025–Feb 2026. Comparing it with the production
   setting separates the window effect from the model change.

**Fair comparison:**

- Use the same June snapshot, actuals, universe and metric code for every model.
- Compare ranking quality with AUC and KS.
- Compare recall and precision at the **same % flagged**, so the 0.025 cutoff and override rules
  don't drive the difference.

**Test labeling happens outside the tool.** The tool only reads
`inference_data/PayoffReason{test+1}.xlsx` and its Refi Yes/No column. Score June loans in the
tool, then evaluate them against the June–August refis separately.

## How labels work

- **Training label:** A loan is a refi if its payoff date falls 0–90 days after its snapshot month
  (`BuildFeatures_new_features.py:243-245`). Both dates are rounded to the 1st of the month, so the
  window covers 3 or 4 calendar months (see F23).
- **Training rows:** Each loan keeps one row, from its latest month in the window (`:101-102`).
- **Training payoff file:** `Combined_Payoff_Data_with_RefinanceYes.xlsx`. Every loan in it is
  treated as a refi, so the file must contain refi payoffs only.
- **Test actuals:** `PayoffReason{YYYY-MM}.xlsx`, Refi Yes/No column. A loan that isn't in the file
  counts as no refi.

## Gotchas

- **Cached files collide.** `training_data_{end}.csv`, `prediction_data_{end}.csv` and
  `best_model_{end}_{universe}.pkl` are named by end date, and the tool silently reuses them if
  they exist (`run.py:89-110`, see F21). Move them aside between runs and between universes.
- **Retraining isn't reproducible.** Optuna has no seed (see F27). Only the data split
  (`random_state=0`) and SMOTE (`42`) are seeded. If an archived `.pkl` exists, use it instead of
  retraining.

## Data request (sent to Gokulnath; files arrive via SharePoint, go in `data/real/` — see MANIFEST)

| # | File | Scope | Format | `data/real/` subfolder |
|---|---|---|---|---|
| 1 | One-Off | Jul 2025 → Jun 2026, one row per loan per month | CSV | `one_off/` |
| 2 | MLW Logins | Dec 2025 → Jun 2026 | CSV | `mlw_logins/` |
| 3 | Credit Bureau | The June 2026 pull only | Excel | `credit_bureau/` |
| 4 | Interest Rate (Curinos) | The full file as it was in June 2026 | Excel | `interest_rate/` |
| 5 | Payoff Data | Dec 2025 → Aug 2026, refi payoffs only | Excel | `payoff_data/` |
| 6 | Payoff Reason Report | Jun, Jul and Aug 2026, as 3 separate files | Excel | `payoff_reason/` |

## New findings

See [known-findings.md](../../docs/context/known-findings.md) F21–F28 (added from this handoff).

## Next tasks

1. ~~Add the findings above to `docs/context/known-findings.md`~~ — done, F21–F28.
2. Plan a read-only evaluation script for the June test. It should compute Recall, legacy
   Specificity, Precision, AUC, KS and % flagged against the June–August refis. Develop it on
   synthetic data only.
3. Write a checklist for running both baselines without cache collisions once the data arrives —
   see `data/real/MANIFEST.md` for a start.
