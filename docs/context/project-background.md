# PG Score — Project Background

Source: Phase 1 audit of real production files (Aug 2026), the original Nov 30, 2023 "ReFinance
Propensity Model Refresh" design deck, process interviews, and direct code reading of the legacy
export (`legacy/`) done 2026-10-16 through 2026-10-19. Where the code contradicts the original
output-file audit, that's called out inline with its evidence — see
[known-findings.md](known-findings.md) for the full findings list this background draws on.

## What PG is

Portfolio Guardian (PG) Score is a **refinance-propensity model**: for each active loan BSI
services, it estimates the probability the borrower refinances (pays off via refi, not sale)
**within the next 90 days**. The output is used to target retention / recapture outreach.

- **Model algorithm: TO CONFIRM** (known-findings.md F11). Three different, mutually-inconsistent
  stories exist and none is verified as the one that produced delivered scores:
  1. **As documented** (2023 design deck / prior audit): Logistic Regression on
     Weight-of-Evidence (WoE) transformed variables; Random Forest used only to filter candidate
     variables, not in production.
  2. **As described in the legacy app's own `README.md`**: an ensemble of Linear Regression and
     Random Forest models.
  3. **As wired in the code**: `run.py` → `TrainingDataPreperation_new_features.py` →
     `modelTraining.py` / `modelTraining_conventional.py` → `ModelInference.py` trains a
     **LightGBM classifier** per universe, with SMOTE oversampling, Optuna hyperparameter search,
     and one-hot encoding of categorical buckets (FICO, LTV, LoanType). No WoE transform exists
     anywhere in `BuildFeatures.py` / `BuildFeatures_new_features.py`.

  Story #3 is the only one that's wired and runnable; story #2 exists in the code
  (`modelTraining_ensemble.py` / `ModelInference_ensemble.py`) but is confirmed dead — both are
  hardcoded to a developer's local Mac path and neither is referenced by `modeling_data/run.py`.
  **Do not treat LightGBM as "the model to preserve" under the no-score-change rule until
  Anwar/process owner confirms which of these three produced the Aug 2026 golden-master output.**
- Retrained **monthly**, described as a **rolling 12-month training window**, tested on the month
  immediately after. The code doesn't quite do this (known-findings.md F16): the training set is
  **one row per loan** — that loan's single most-recent snapshot inside `[st_date, end_date]`, not
  a 12-month panel — and the window itself is `(st_date, end_date]`, with `st_date` **exclusive**,
  so a `st_date="2024-05"`/`end_date="2025-04"` run actually spans 2024-06 through 2025-04:
  **11 months, not 12**. See F17, F18, F20 for further label-construction findings.
- Run **separately per loan universe**:
  - **Conventional**
  - **"FHA"** — actually contains FHA **and VA** loans; called "GNMA" in some process notes.
- Output per loan: `pred_prob` (probability) and `y_pred` (Yes/No flag at a cutoff).

## Label (target)

- Forward 3-month (90-day) payoff window from the observation date.
- Documented as: refi vs. sale distinguished via `Reason_Closed_Redifn` (from the Payoff Reason
  report). **The code doesn't do this** (known-findings.md F18): the label counts *any* payoff
  within 90 days — refinance, sale, REO, or short sale alike. `Reason_Closed`/`Reason_Closed_Redifn`
  are loaded but never used to filter the label in the wired feature-building code; an older,
  unwired version of that code did filter on them.
- Loans already closed as of the observation date are excluded (no leakage by design).

## Current monthly process (as-is)

1. Gather six business-described inputs:
   - **Loan One-Off** — SQL from Asset360
   - **Credit Bureau** — SQL from Asset360
   - **MLW Login** — SQL from Asset360 (MyLoanWeb borrower portal logins)
   - **Loan Payoff** — SQL from Asset360
   - **Payoff Reason Report** — internal report
   - **Market rate** — documented as Freddie Mac; actually a manually updated Curinos file

   The code actually reads **9** local files, not 6 — see "Legacy app stack" below for the full
   list and a reconciliation of which of the 9 map to these 6 named inputs.
2. Upload the files into the internal **"Modeling Parameters" tool** — documented as a Flowise app
   on an AWS EC2 load balancer, served over plain HTTP. **The legacy export is a plain Flask app**
   (`legacy/app.py`) that shells out to CLI scripts via `subprocess` — not Flowise. An exhaustive
   grep across every `.py` file in the export for Flowise, Databricks/DBFS, SQL, boto3, `requests`,
   and socket code found zero matches. `README.md`'s own Databricks DBFS section
   (`DATABRICKS_HOST`/`DATABRICKS_TOKEN`) has no corresponding code anywhere in this export — it's
   stale, or describes something not included here. Still open: why the process docs and this
   app's own README both describe infrastructure that doesn't exist in the code — ask Anwar/IT
   whether an unexported upstream layer exists, or the documentation is simply wrong.
3. Set Start / End / Test dates in the tool; run once per universe.
4. Tool retrains, scores, and shows metrics (Recall, "Specificity").
5. Previous model `.pkl` is archived by **manual renaming** — no registry or versioning. Matches
   the code — see model artifact path/format below.
6. Conventional + FHA predictions are combined into a final 3-column report and shared monthly
   with Anwar (process owner).

Scale (Aug 2026): Conventional 70,918 loans; FHA 33,776 loans; combined report 104,694 loans.

### Legacy app stack

Confirmed by a full read of every file in `legacy/` (code, templates, `.gitignore`, the one
Jupyter notebook) plus an exhaustive grep for database/cloud/network code:

- **Pipeline order:** `legacy/app.py` (Flask, port 8000) → `subprocess` → `modeling_data/run.py` →
  `data_preperation/TrainingDataPreperation_new_features.py` (feature build) →
  `Modeling/modelTraining.py` (FHA) / `modelTraining_conventional.py` (Conventional) (training) →
  `Modeling/PredictionDataPreperation.py` (scoring features) → `Modeling/ModelInference.py`
  (scoring + final `y_pred`). Conventional + FHA outputs are then merged by the separate
  `combine_predictions.py` script. Evidence: `app.py:112-113` (calls `run_model_with_params`) →
  `modeling_data/run_model.py:14,22` (invokes `run.py` via `subprocess`) →
  `modeling_data/run.py:57-61` (defines the script paths above) → `app.py:208-219` (separately
  invokes `combine_predictions.py` from the `/run-combine-predictions` route).
- **9 local files actually read by the code:**

  | File | Path | Read at |
  |---|---|---|
  | Main loan extract | `inference_data/one_off_oct23_to_Feb25.csv` | `Modeling/PredictionDataPreperation.py:55`, `data_preperation/TrainingDataPreperation_new_features.py:17` |
  | Payoff reason files | `data_preperation/Input/Payoffs Reasons/*.xlsx` | `data_preperation/BuildFeatures_new_features.py:137-183` |
  | Market rate matrix | `data_preperation/Input/Curinos_Interest_Rate_File_2022-2024.csv` (training) / `inference_data/Interest Rate Data.xlsx` (scoring) | `TrainingDataPreperation_new_features.py:19`, `PredictionDataPreperation.py:71` |
  | Credit bureau report | `inference_data/BSI_CREDITREPORTING.xlsx` | `BuildFeatures_new_features.py:424` |
  | Login activity | `inference_data/MLW_logins.csv` | `TrainingDataPreperation_new_features.py:21` |
  | ZIP→FIPS lookup | `data_preperation/Input/Zip_FIPS_Mapping.csv` | `TrainingDataPreperation_new_features.py:22` |
  | Census demographics | `data_preperation/Input/Census_Demographic.csv` | `TrainingDataPreperation_new_features.py:23` — **60 columns required in a fixed order** (`clean_domographic()`, `BuildFeatures_new_features.py:621-685`). Only 3 of the 60 ever reach the model's features; see Feature provenance below. |
  | House price index | `data_preperation/Input/HPI.xlsx` | `TrainingDataPreperation_new_features.py:24` — joined (`:151`) but **no HPI-derived column reaches the final feature list** (`:170-178`); it never reaches training or scoring. |
  | Monthly label file | `inference_data/PayoffReason{YYYY-MM}.xlsx` | `Modeling/ModelInference.py:69` |

  Both the Census and HPI merges are `how='left'` (`TrainingDataPreperation_new_features.py:150-151`)
  — neither can silently drop a loan row for a missing geography/HPI match; a miss just leaves
  those columns `NaN` (see F8 for the Census missing-rate finding).

  **6-vs-9 reconciliation (TO CONFIRM):** 5 of the 9 map reasonably cleanly onto the 6 named
  business inputs — Main loan extract → Loan One-Off; Credit bureau report → Credit Bureau;
  Login activity → MLW Login; Market rate matrix → Market rate; Payoff reason files / Monthly
  label file → Payoff Reason Report (the same report type used at training time and again at
  scoring time to backtest Recall/Specificity, not two separate inputs). The 3 geography files —
  ZIP→FIPS lookup, Census demographics, House price index — are **static/low-frequency reference
  data** joined in during feature building; they aren't named as inputs in the 6-item business
  description because they aren't part of the monthly SQL/report refresh cycle. That leaves the
  **"Loan Payoff" business input (SQL from Asset360) unaccounted for** — no distinct file for it
  exists in this code. It may be the same report as "Payoff Reason Report" under a different name,
  or genuinely missing from this export. **TO CONFIRM with Anwar/data engineering.**
- **Model artifact path and format:** saved to
  `Modeling/BestModel/best_model_{end_date}_{data_universe}.pkl` via
  `joblib.dump({"model": <fitted LightGBM classifier>, "best_threshold": <float>}, path)`
  (`Modeling/modelTraining.py:263-272`, `modelTraining_conventional.py:265-274`); loaded the same
  way in `Modeling/ModelInference.py:61-65`. No registry or versioning beyond this filename —
  matches the "manual renaming" process description above. The loaded `best_threshold` is never
  actually used for the delivered `y_pred` — see known-findings.md F12.
- **Ensemble code (Linear Regression + Random Forest) is confirmed dead code**, not an alternate
  production path: `Modeling/modelTraining_ensemble.py` / `ModelInference_ensemble.py` are
  hardcoded to a developer's local Mac path (`/Users/abhilashchenreddy/...`), save/load their own
  separately-named `.pkl` files (`lr_ensemble.pkl`, `rf_ensemble.pkl`, `scaler.pkl`,
  `imputer.pkl`), and are never invoked by `run.py` or `app.py` (`modeling_data/run.py:57-61` lists
  every script path `run.py` can reach, and neither file is in it).
- **Python 3.10+ required**, not "3.8+" as `README.md` states — `requirements.txt:23` pins
  `numpy==2.2.6`, which requires Python ≥3.10. No Node/JS anywhere in the export.
- **The legacy export is code-only:** 24 files, no `.xlsx`/`.xls`/`.csv` anywhere, commit message
  `"data and model artifacts excluded"`. Real inputs must be supplied separately on an approved
  BSI machine.

## Columns in the production files

LoanNumber, LoanType, CREDIT_BUREAU_PAYMENT_HISTORY, PrincipalBalance, Is_MailingZip_Equal_PropZip,
FICO_Score, CurrentLTV, Login_Count, Interest_Delta_Current_Market, Ltv_Delta_Orginal_Current,
PropertyState, FICO_Difference, EscrowPayment_Flag, Flag_Trailing_DaysDiff_GT45,
3 Census ACS fields (education %, mean household income in "2021 inflation-adjusted dollars",
owner-occupied %), pred_prob, "Loan Number" (duplicate, almost always blank), Refi_flag, y_pred.

Note the spelling `Ltv_Delta_Orginal_Current` (sic) — keep it; downstream consumers may depend on it.

### Feature provenance

- 12 predictors were the validated set in the 2023 design; the set has been essentially frozen
  since.
- **4 fields in production are not in the 2023 design** and have no record of when/why they were
  added: PropertyState, FICO_Difference, EscrowPayment_Flag, Flag_Trailing_DaysDiff_GT45. The
  latter three are all computed together by `calculate_flags()` in
  `data_preperation/BuildFeatures_new_features.py` (a trailing-6-month self-merge on loan number);
  that function doesn't exist in the older `data_preperation/BuildFeatures.py`, so it was added
  some time after the original build. Still no record of *when* or *why* — only the code location
  is known.
- `Interest_Delta_Current_Market` = note rate − market rate. **For ~97%+ of loans this "market
  rate" is looked up against a hardcoded Jun-2023 date, not the loan's real observation month** —
  see known-findings.md F14.
- Census fields are area-level (not borrower-level), joining on **ZIP→county FIPS**
  (`add_fips_to_training_oneoff()` joins `PropertyZipCode` → `STCOUNTYFP`, then demographics join
  on that FIPS code). The House Price Index / purchase-index file joins separately, at the
  **state** level (`PropertyState` + observation month). Both join levels mentioned in the 2023
  deck are in use today, just for two different files, not one inconsistency.

## Known backtest (Jul 2025, FHA universe — the only one with known outcomes)

| Item | Value |
|---|---|
| Loans | 28,114 |
| Actual refis | 88 (0.31% base rate) |
| Flagged "Yes" | 9,500 (~34% of portfolio) |
| True positives | 63 |
| Recall | 0.716 (matches tool) |
| Precision | ~0.66% (not reported by tool) |
| Tool "Specificity" | 0.3379 — equals % flagged, not TN/(TN+FP) |
| True specificity TN/(TN+FP) | 0.6633 (for reference only; tool formula is kept) |

## Where this is going

- **Stage 1 (this repo):** move the existing process off Flowise into a tested, versioned Python
  pipeline with the same behavior. Parity target: reproduce Aug 2026 exactly, then two matching
  parallel months (Nov, Dec) before Flowise is switched off (proposed Dec 14, 2026).
- **Source control:** GitHub (private, BSI org) now; Azure DevOps (Repos + Pipelines, self-hosted
  agent, Blob Storage, Key Vault, SQL Server) later.
- **Out of scope here:** model improvements (new features, deciles, calibration, new algorithms,
  live rate feed). Those are separate, later work.
