# Glossary

| Term | Meaning |
|---|---|
| **PG / Portfolio Guardian** | BSI's refinance-propensity score for serviced loans |
| **BSI** | BSI Financial Services — mortgage servicer / subservicer |
| **Asset360** | BSI's servicing system of record; source of 4 of the 6 inputs via SQL |
| **MLW / MyLoanWeb** | BSI's borrower web portal; `Login_Count` comes from its login data |
| **Modeling Parameters tool** | Internal Flowise app (EC2, HTTP) where inputs are uploaded and the model is trained/scored today |
| **Flowise** | Low-code flow builder the current tool is built on; being retired in Stage 1 |
| **Universe** | A separately trained/scored loan population: Conventional, or "FHA" (FHA + VA) |
| **GNMA** | Ginnie Mae; government-backed loans (FHA, VA). Some notes call the FHA universe "GNMA" |
| **Conventional** | Loans not government-insured (Fannie Mae / Freddie Mac / portfolio) |
| **Refi / Refi_flag** | Loan paid off via refinance within the 90-day label window |
| **Recapture** | BSI (or the client) originating the new loan when a borrower refinances |
| **pred_prob** | Model's predicted probability of refi |
| **y_pred** | Yes/No flag derived from the probability at a cutoff |
| **WoE (Weight of Evidence)** | Binning transform: each bin of a variable is replaced by ln(%non-events / %events) or similar. Coefficients apply to WoE values, not raw values |
| **Rolling 12-month window** | Each month the model is retrained on the prior 12 months of observations |
| **Golden master** | Saved reference outputs (Aug 2026) that the new pipeline must reproduce exactly. Repo stores hashes + summary metrics only |
| **Run manifest** | JSON record of a run: input file hashes, git commit, library versions, model hash, metrics, row counts |
| **Curinos** | Market-rate data vendor; current (stale, manual) rate source |
| **PMMS** | Freddie Mac Primary Mortgage Market Survey — the documented intended rate source |
| **ACS / Census fields** | Area-level American Community Survey demographics joined by geography |
| **LTV** | Loan-to-value ratio |
| **FICO** | Credit score |
| **Specificity (tool)** | The legacy tool's metric labelled "Specificity". Kept as-is. It equals the share of loans flagged "Yes", not TN/(TN+FP) |
| **Precision** | TP / (TP + FP) — share of flagged loans that actually refinanced (new metric) |
| **Recall** | TP / (TP + FN) — share of actual refis that were flagged |
| **AUC** | Area under the ROC curve on `pred_prob` (new metric) |
| **KS** | Kolmogorov–Smirnov statistic: max gap between cumulative score distributions of refis vs. non-refis (new metric) |
| **ADR** | Architecture Decision Record (`docs/adr/`) |
