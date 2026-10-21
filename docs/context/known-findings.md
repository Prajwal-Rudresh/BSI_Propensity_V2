# Known Findings and Open Questions

Confirmed defects and open questions for the legacy PG Score pipeline (`legacy/`), combined from
the Aug 2026 output-file audit, the 2023 design-deck gap analysis, and direct code reading done
2026-10-16 through 2026-10-19. Each finding below is cited to a file and line — Step 4 should
re-verify the still-unconfirmed ones against real data before any fix.

Labels: `no-score-change` = safe to fix in normal review. `needs-signoff` = changes delivered
scores or model inputs; branch + before/after diff + Anwar approval required.
`document-only` = record behavior, do not change.

Organized in two sections: **A. Code defects** (labeled `no-score-change` or `needs-signoff` —
things that can and eventually will be fixed) and **B. Model design** (labeled `document-only` —
properties of how the model/label/process currently work, not bugs to fix).

## A. Code defects (fix: no-score-change or needs-signoff)

| # | Severity | Summary | Label |
|---|---|---|---|
| [F1](#f1) | Critical | `pred_prob`/`y_pred` disagree for ~1/3–37% of loans | needs-signoff |
| [F5](#f5) | High | `Flag_Trailing_DaysDiff_GT45` is always 0 | needs-signoff |
| [F6](#f6) | High | `Login_Count` missing for 47–67% of loans | needs-signoff if join broken |
| [F7](#f7) | Medium | Duplicate, blank "Loan Number" column | needs-signoff if affects joins |
| [F12](#f12) | Critical | F1's mechanism: hardcoded 0.025 threshold + 3 override rules | needs-signoff |
| [F13](#f13) | High | Credit-history slice drops oldest column, zero-fills newest | needs-signoff |
| [F14](#f14) | High | `Interest_Delta_Current_Market` uses a hardcoded lookup date for ~97% of loans | needs-signoff |
| [F15](#f15) | Medium | SMOTE crashes if the refi share exceeds `sampling_strategy` | document-only (missing guardrail) |
| [F18](#f18) | High | Label counts sales/REO/short-sales as refis — regression from older code | needs-signoff |
| [F19](#f19) | High | Loan-number typing is inconsistent across inputs (int64 vs. uncast) — join/collision risk | needs-signoff if join broken |

### F1
`pred_prob` and `y_pred` disagree for ~1/3–37% of loans (Conv Aug26, FHA Aug26, FHA Jul25 all show
this). Mechanism found — see **F12**. `Modeling/ModelInference.py:271-282`.

### F5
`Flag_Trailing_DaysDiff_GT45` is always 0 (zero variance) across 130K+ loans in every real file
checked. Suspected cause (unconfirmed against real data): `load_and_preprocess_mck_data` processes
the source CSV in 100k-row `chunksize` chunks and calls `calculate_flags()` per chunk, so the
trailing-6-month self-merge can only see history within the same chunk — a loan whose prior
observations land in an earlier chunk never gets `Days_Diff_past` populated. Fixing this changes a
model input. `data_preperation/BuildFeatures_new_features.py:690-775`.

*Related:* `EscrowPayment_Flag` (computed by the same function) was also thought zero-variance, but
the Jul 2025 backtest shows it fires for 0.5% of loans — it's **rare, not broken**. Don't flag it
as a defect.

### F6
`Login_Count` is missing for 47–67% of loans across every real file checked. Unconfirmed whether
that's a true zero (no logins) or a broken join — e.g. the integer-cast of `LoanNumberPlain` after
stripping a leading `-` (`BuildFeatures_new_features.py:516`, applied again at
`TrainingDataPreperation_new_features.py:140`) could silently collide two different loans into one
key — see **F19** for the full loan-number-typing picture across every input. `Monthly_Login_Count`
is built by `count_monthly_logins()` in `BuildFeatures_new_features.py` and merged in
`TrainingDataPreperation_new_features.py:167` on
`['LoanNumber','Year_Month_Obs'] = ['LoanNumberPlain','Login_Year_Month']`.

### F7
A duplicate "Loan Number" column, ~100% blank, appears in every real file checked — join-key
fragmentation. Not yet traced to its origin in the six-input pipeline itself;
`combine_predictions.py` (the Conv+FHA report combiner) defensively accepts either `LoanNumber` or
`Loan Number`, suggesting downstream awareness of the duplicate without explaining where it comes
from.

### F12
**F1's mechanism.** `y_pred` is not `pred_prob >= saved best_threshold` — `ModelInference.py` loads
`best_threshold` from the trained model file (`:60-65`) but never uses it again (confirmed dead by
grep). The actual delivered `y_pred` (`:271-282`) uses a **hardcoded threshold of 0.025** plus
three hardcoded override rules applied in sequence:
- `Interest_Delta_Current_Market < -1` force-flips Yes→No
- `Ltv_Delta_Orginal_Current > 25` force-flips No→Yes
- `FICO_Difference > 500` force-flips No→Yes

Any change to the threshold or override constants changes delivered scores (needs-signoff). Two of
the file's three threshold-sweep functions are also dead code or unused output — see
[docs/investigations/model-and-threshold.md](model-and-threshold.md) for the full trace, including
why this is the leading (but not fully data-confirmed) explanation for F1.

### F13
**Credit-history positional slice silently drops the oldest real history column and always
zero-fills the newest "history" slot.** `process_credit_report()` calls `.reset_index()` on the
filtered credit report (`:439`), which inserts a new `index` column at position 0 — shifting every
later positional reference by one. `start_date`/`end_date` are then appended as the new last two
columns (`:442-447`). `transform_credit_report_to_time_series()`'s `.iloc[:, -37:-1]` slice
(`:406`) is meant to grab the 36 monthly payment-history values, but because of the `reset_index()`
shift, position -2 (the slice's last element) is always `start_date` (a `Timestamp`, not a real
history code) and the true oldest history column is always excluded entirely. Since `start_date`
fails the `valid_values` whitelist, it's coerced to `0` — so every loan's
`CREDIT_BUREAU_PAYMENT_HISTORY` summary is built from 35 real months plus one
structurally-guaranteed zero, not 36 real months. Fixing this changes a model input for every loan.
`data_preperation/BuildFeatures_new_features.py:439,442-447,406`.

### F14
**`Interest_Delta_Current_Market` is computed against a hardcoded market-rate lookup date for
~97%+ of loans, not the loan's real observation month.** `merge_and_process_data()` defaults every
loan's `Event_Date` to the literal string `"2023-08"` whenever it has no matching payoff-reason
record — i.e. every loan *not* being labeled "refinanced" this window, the large majority (`:233`).
`Interest_Rate_Date` is then `Event_Date - 2 months` = `"2023-06"` (`:238-240`), and
`bucket_and_transform_data()` uses that date's `Year`/`Month` as the interest-rate-matrix lookup
key (`:280-281`). So for most of the training population, the "current market rate" is always the
Jun-2023 rate, regardless of real observation month — only the small minority with a matching
payoff record gets a realistic, payoff-month-relative lookup date. The existing
group-mean/per-LoanType-mean fallback (`TrainingDataPreperation_new_features.py:104-128`) keeps
this from crashing or nulling out, it just makes the feature far less time-varying than its name
implies. Not yet checked against real data. Fixing changes a model input for the majority of loans.

### F15
**Candidate finding, reproduced but not yet checked against real production data.** Training
crashes outright if the refi share in the training window exceeds SMOTE's `sampling_strategy`
ceiling for that universe (e.g. a genuine refi boom, or a date-window mistake that concentrates too
many payoffs in one window). `imbalanced-learn`'s `SMOTE` requires the input minority:majority ratio
to be *below* `sampling_strategy` — it only oversamples the minority, so it can't reach a target
ratio that's already exceeded. Reproduced directly: an early draft of `scripts/make_synthetic.py`
hit this exactly (FHA: 470 positives / 1400 negatives = ratio 0.34, far above the 0.1 ceiling) and
crashed `modelTraining.py` at the `smote.fit_resample(...)` call. This describes a missing
guardrail, not a scoring defect to fix without signoff — adding one (e.g. clamping
`sampling_strategy` or validating the ratio first) would itself need the needs-signoff process,
since it changes training behavior.
`Modeling/modelTraining.py:81` (`sampling_strategy=0.1`, FHA), `:82` (`fit_resample`);
`Modeling/modelTraining_conventional.py:81` (`sampling_strategy=0.2`, Conventional), `:82`
(`fit_resample`). Neither file overrides `k_neighbors` (confirmed via grep), so both also require
>=6 real minority training samples (imbalanced-learn's SMOTE default `k_neighbors=5`).

### F18
**Label counts any payoff within 90 days — including sales, REO, and short sales — not just
refinances. Regression from the older, unwired `BuildFeatures.py`.** `filter_and_clean_final_data()`
in the wired `BuildFeatures_new_features.py` (`:186-203`) — which cleans the payoff-reasons data
before it's merged into training — never references `Reason_Closed` or `Reason_Closed_Redifn`; it
only dedupes by most-recent `Date_Paid_Off`. `merge_and_process_data()` (`:205-268`) then computes
the label purely from date arithmetic, never touching either reason column, and doesn't even carry
them into its own output. Both columns are loaded upstream (`process_all_files()`'s
`final_columns` aliases, `:154-155`) and then silently dropped.

**What "restore" would look like:** the older, unwired `data_preperation/BuildFeatures.py` *did*
filter on these columns, in its own `filter_and_clean_final_data()` —
`:174` excludes `Reason_Closed == "REO"` or `"SS"`; `:177-185` normalizes `Reason_Closed_Redifn`
(lowercased, stripped) and keeps only rows where it's in
`["off market", "not found", "for rent", "not available", "offmarket", "house for rent", "rent"]`.
**Caveat:** that whitelist reads like property marketing/occupancy status values, not obviously
"is this a refinance" — so even restoring this exact filter isn't self-evidently "keep only true
refinances." What `Reason_Closed_Redifn`'s values actually represent needs confirming (e.g. with
Anwar/data engineering), not assumed from the old code's behavior alone.

Net effect today: a loan that pays off via sale, REO, or short sale within 90 days gets the exact
same positive label as a genuine refinance — contradicting project-background.md's "Refi vs. sale
distinguished via `Reason_Closed_Redifn`" claim. Fixing this changes delivered labels/scores
(needs-signoff).

### F19
**Loan-number typing is inconsistent across every input source — a real, demonstrated join/collision
risk, not just a hypothesis.** No explicit `dtype`/converter is set when reading the main loan
extract (`BuildFeatures_new_features.py:38`, `pd.read_csv(..., chunksize=chunk_size)`) or the
credit bureau report (`:120`, `:436`, `pd.read_excel(file_path)`) — both rely on pandas' default
type inference, almost certainly `int64` for the loan extract (silently dropping any leading
zeros), unconfirmed for the credit report (depends on upstream Excel cell formatting). The payoff
reason files are explicitly cast to `int64` (`:201`). MLW logins get a stranger treatment:
`.astype(int)` (`:516`), then a second pass that does
`.astype(str).str.replace(r'^-','',regex=True).astype(int)`
(`TrainingDataPreperation_new_features.py:140`, `PredictionDataPreperation.py:126`) — stripping a
**leading minus sign** before re-casting. The monthly label file's `Loan Number` column
(`Modeling/ModelInference.py:68-71`) is never cast at all before being merged against `LoanNumber`
(`:101`).

Two concrete, code-confirmed mechanisms (not speculative):
1. The minus-sign-strip means a login record keyed `"-12345"` and one keyed `"12345"` **collide
   into the same loan** after transformation.
2. The inference-time label merge (`ModelInference.py:101`) has no cast on either side — if the
   label file's `Loan Number` column is read as text/object while `LoanNumber` is `int64`
   (plausible if that column is Excel-formatted as text), the merge finds **zero matches**, and
   `:103`'s `.fillna(0)` silently sets every loan's ground-truth `Refi_flag` to `0` with no error
   raised — corrupting the Recall/Specificity metrics shown in the UI.

Needs-signoff if confirmed against real data to actually be causing mismatches (Step 4); CLAUDE.md's
own code standard already requires loan numbers to be strings everywhere, which this pipeline
doesn't currently follow in any of its five input sources.

## B. Model design (document only)

| # | Severity | Summary | Label |
|---|---|---|---|
| [F2](#f2) | Critical | Flagged list is >99% false alarms | document-only |
| [F3](#f3) | High | "Specificity" = % flagged, not TN/(TN+FP) | document-only |
| [F4](#f4) | High | Market rate is stale Curinos data, not Freddie Mac | document-only |
| [F8](#f8) | Medium | 3 Census fields missing 13.6–16% | document-only |
| [F9](#f9) | Low | "FHA" universe includes VA loans | document-only |
| [F10](#f10) | Security | Tool served over plain HTTP | no-score-change (moot — resolved by leaving the tool) |
| [F11](#f11) | Critical | Documented model algorithm ≠ wired code — **TO CONFIRM** | document-only |
| [F16](#f16) | Medium | Training set is 1 row/loan over 11 months, not a 12-month panel | document-only |
| [F17](#f17) | Medium | Positives/negatives observed at systematically different months | document-only |
| [F20](#f20) | Medium | Possible right-censoring at `end_date` — **needs production timing confirmation** | document-only |

### F2
The flagged ("Yes") list is >99% false alarms: precision ~0.66%, ~34% of the portfolio flagged
(2023 design target was ≤40%, ideally 10–20%). Threshold is out of scope to change — this is a
direct consequence of F12's threshold/override constants, same location.

### F3
The tool's "Specificity" equals `(TP+FP)/(TN+TP+FP+FN)` — the share of loans flagged "Yes" — not
`TN/(TN+FP)`. Precision, AUC, and KS aren't reported at all. Keep the existing formula as-is
(hard rule #3); add Precision/AUC/KS/% flagged as new, additive columns (no-score-change).
Appears identically in three places: `Modeling/modelTraining.py`, `modelTraining_conventional.py`,
and `Modeling/ModelInference.py`.

### F4
The "market rate" is a stale, manually extrapolated Curinos file, not the documented Freddie Mac
rate. Out of scope here (a separate ADR covers the rate feed), but a freshness check should be
added. File: `data_preperation/Input/Curinos_Interest_Rate_File_2022-2024.csv` (training) /
`inference_data/Interest Rate Data.xlsx` (scoring), read in `TrainingDataPreperation_new_features.py`
and `Modeling/PredictionDataPreperation.py`.

### F8
The 3 Census ACS fields are missing 13.6–16% of the time; the vintage of `Census_Demographic.csv`
is undocumented and not resolvable from code alone. Join logic: `clean_domographic()` / FIPS join
in `BuildFeatures_new_features.py`. The join itself is `how='left'` and can't silently drop loan
rows for a missing match (confirmed 2026-10-19, `TrainingDataPreperation_new_features.py:150-151`)
— a miss just leaves these columns `NaN`.

### F9
The "FHA" universe actually includes VA loans too, and is called "GNMA" in some process notes —
naming only. Hardcoded as `bucket = ["FHA", "VA"]` in `TrainingDataPreperation_new_features.py`,
`Modeling/modelTraining.py`, `Modeling/PredictionDataPreperation.py`, `Modeling/ModelInference.py`.

### F10
The "Modeling Parameters" tool is documented as served over plain HTTP while handling FICO/credit
data. Resolved by leaving this tool behind (no-score-change either way). What the code shows
(2026-10-19): it's a Flask app run via its own dev server (`legacy/app.py:595`, `debug=True`), with
no TLS config anywhere in the export — this neither confirms nor refutes the original "EC2 load
balancer, plain HTTP" claim, since no deployment/infra config exists in this export to check
against.

### F11
**Status: TO CONFIRM.** The documented model algorithm doesn't match the wired production code,
and in fact three different, mutually-inconsistent stories exist:
1. **As documented** (2023 design deck / prior audit): Logistic Regression on Weight-of-Evidence
   (WoE) transformed variables; Random Forest used only to filter candidate variables.
2. **As described in the legacy app's own `README.md`**: an ensemble of Linear Regression and
   Random Forest models.
3. **As wired in the code**: `run.py` → `TrainingDataPreperation_new_features.py` →
   `modelTraining.py` / `modelTraining_conventional.py` → `ModelInference.py` trains a
   **LightGBM classifier** with SMOTE oversampling and Optuna hyperparameter search. No WoE
   transform exists anywhere in `BuildFeatures.py` / `BuildFeatures_new_features.py`.

Story #3 is the only one that's wired and runnable. Story #2 exists in code
(`modelTraining_ensemble.py` / `ModelInference_ensemble.py`) but is **confirmed dead**: both are
hardcoded to a developer's local Mac path (`modelTraining_ensemble.py:15,193`,
`ModelInference_ensemble.py:11-16,129-130`), and neither filename appears in
`modeling_data/run.py:57-61`, the only place script paths are wired.

**Do not treat LightGBM as "the model to preserve" under the no-score-change rule until
Anwar/process owner confirms which of these three produced the Aug 2026 golden-master output.**
This affects the premise of hard rule #2 and should be resolved before Step 3 (golden master)
parity work.

### F16
**The training set is one row per loan, over 11 months, not a 12-month panel.**
`mck_data_selected.sort_values(['Year_Month_Obs']).groupby(['LoanNumber']).last()`
(`BuildFeatures_new_features.py:101-102`) collapses every loan to its single most-recent
qualifying month. And `filter_data_by_date_range()`'s window is `(start_date, end_date]` —
`start_date` is **exclusive** (`:73`, strict `>`), `end_date` inclusive — so
`st_date="2024-05"`/`end_date="2025-04"` actually keeps 2024-06 through 2025-04: **11 months, not
12**. (See **F18** for a related but separate finding — the label itself counting non-refi
payoffs — split out from this one.)

### F17
**Candidate finding, not yet tested against real data.** Positive and negative training rows are
implicitly observed at systematically different months. A row is positive only if `Date_Paid_Off`
falls within 90 days *after* that loan's `Year_Month_Obs` (its single selected snapshot month, see
F16) — so positives are, by the label's own definition, anchored close to their payoff event.
Negatives carry whatever month happened to be each loan's last-in-window snapshot, commonly
`end_date` itself for loans still active then. A positive and a negative loan with otherwise
identical characteristics can therefore differ in `Year_Month_Obs` — and in anything derived from
it, e.g. `Interest_Delta_Current_Market` via `Interest_Rate_Date` (see F14) — purely from this
timing artifact, not a genuine behavioral difference. Risk: the model may partly learn "is this
observation month near a payoff event" rather than "is this loan propensity-to-refinance," which
wouldn't transfer to scoring time, where every loan is observed at the same fixed `test_date`.
`merge_and_process_data()`, `BuildFeatures_new_features.py:228-250` (label/date-diff computation),
`:243` (`Year_Month_Obs`).

### F20
**Candidate finding — status: needs production data-timing confirmation.** A loan still open at
`end_date` that genuinely refinances shortly *after* the window (e.g. 10 days past `end_date`,
still within its true 90-day lookahead) is labeled `0` here only because no matching payoff record
exists yet in `all_payoff_reason_data` when this window's training data is built —
`Date_Paid_Off` becomes `NaT` on no match (`errors="coerce"`, `:229`), `Date_Diff_Days` is then
undefined (`:245`), and the label defaults to the negative class (`:248-250`). This is a possible
right-censoring issue, but whether it's a real risk in production depends entirely on **how far
forward payoff-reason data is available relative to `end_date`** when a given month's training
actually runs — not determined by code reading alone. Do not treat as a confirmed defect until
confirmed with Anwar/data engineering.

## Hypotheses tested for F1 (pred_prob / y_pred mismatch)

The real mechanism was found directly in code (F12) rather than by testing these one by one — kept
here since the override mechanism doesn't rule out these contributing additional disagreement.

1. `y_pred` from a different or stale model than `pred_prob` (manual `.pkl` renaming) — untested.
2. Row misalignment after a merge/sort (e.g. the blank duplicate "Loan Number" column, or an index
   reset after filtering) — untested. See **F19** for a now-concrete version of this: loan-number
   typing/collision risk across every input, not just row-order risk.
3. ~~`y_pred` from `model.predict()`'s implicit 0.5 cutoff~~ — refined by F12: it's a hardcoded
   0.025, not 0.5, plus three override rules on top.
4. ~~WoE bins refit at scoring time vs. training time~~ — moot: no WoE transform exists anywhere in
   the feature-building code (F11); the model one-hot encodes FICO/LTV buckets instead.
5. Type issues on the loan number key (float conversion, lost leading zeros) — **see F19**, now
   confirmed as a real mechanism (not just a hypothesis), though not yet confirmed to explain F1
   specifically.

## Likely code-level issues to look for (Step 4 checklist)

- Hardcoded dates, months or file paths (a Dec 2024 review found hard-coded references that made
  training read stale data — see F14 for a confirmed instance).
- `merge` without row-count assertions or `validate=` (e.g. the test-data merge in
  `ModelInference.py:101` has no `validate=` — see F19).
- `fillna(0)` that may convert "missing" `Login_Count` into "zero logins" (see F6), or a failed
  join into a false "No" label (see F19).
- Silent `dropna` that changes the scored population.
- WoE fit on train+test together (leakage) — moot, see F11.
- Missing random seeds.
- Bare `except` / swallowed errors.
- Credentials or connection strings in the flow or code — none found (see project-background.md).
- SQL built by string concatenation — no SQL exists in this export at all.
- Copy-pasted Conventional vs. FHA logic that has drifted apart — confirmed in SMOTE ratio and
  Optuna search space, see docs/investigations/model-and-threshold.md §6.
- Loan numbers cast to int instead of kept as strings — confirmed in 3 of 5 input sources, see F19.

## Open questions (do not treat as settled)

- **Who set the F12 threshold/override constants (0.025, -1, 25, 500) and why**, and are they the
  same ones that produced the Aug 2026 golden-master files we need to reproduce?
- Is missing `Login_Count` (F6) a true zero or a broken join?
- Origin and validation history of PropertyState, FICO_Difference, EscrowPayment_Flag,
  `Flag_Trailing_DaysDiff_GT45` — code location is known (F5, F9), but *when/why* they were added
  to the validated feature set is still undocumented.
- What does `Reason_Closed_Redifn` actually represent (see F18)? The old filter's whitelist values
  don't read as obviously refi-related — confirm its real meaning before using it to "fix" F18.
- Is `requirements.txt`'s pinned environment (Python 3.10+, scikit-learn 1.6.1, lightgbm 4.6.0,
  etc.) the exact one that produced the Aug 2026 `.pkl` files, or a later dev snapshot?
- Why do the process docs and the legacy app's own `README.md` both describe infrastructure
  (Flowise+EC2, Databricks DBFS) that doesn't exist anywhere in the exported code (confirmed via
  exhaustive grep, 2026-10-19)? Is there an unexported upstream layer, or is the documentation
  simply wrong? Ask Anwar/IT.
- Which of F11's three described algorithms actually produced the Aug 2026 golden-master files?
- How far forward is payoff-reason data actually available relative to a given month's `end_date`
  in production? Determines whether F20's possible right-censoring is real — needs Anwar/data
  engineering confirmation, not resolvable from code alone.
- The "Loan Payoff" business input (SQL from Asset360) is still unaccounted for in the code — see
  project-background.md's 6-vs-9 reconciliation.

When one is answered, move it into project-background.md with its source and date.
