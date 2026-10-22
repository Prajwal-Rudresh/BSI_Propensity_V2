# Full EDA report (aggregate-only, auto-generated)

### Is payoff_data already refi-only? (F18/F25)

- `ReasonClosed` value counts: {'PIF': 3015, 'RELEASED': 5}
- `Reason Closed_Redfin` value counts: {'Off Market': 2985, 'Not Found': 20, 'For Rent': 15}
- `Refinance` value counts: {'Yes': 3020}

### Loan-number dtype audit (F19)

| file | column | dtype |
|---|---|---|
| one_off_trimmed_2025-07_2026-06.csv | LoanNumber | int64 |
| mlw_logins_trimmed_2025-12_2026-06.csv | LoanNumber | int64 |
| Credit Bureau Data.csv | ACCT_NBR | int64 |
| Combined_Payoff_Data_with_RefinanceYes.xlsx | LoanNumber | int64 |

### Null rates — same_window_2026-02

| column | null % |
|---|---|
| LoanType | 0.0% |
| CREDIT_BUREAU_PAYMENT_HISTORY | 0.0% |
| PrincipalBalance | 0.0% |
| Is_MailingZip_Equal_PropZip | 0.0% |
| FICO_Score | 0.0% |
| CurrentLTV | 0.0% |
| Login_Count | 57.2% |
| Interest_Delta_Current_Market | 3.1% |
| Ltv_Delta_Orginal_Current | 0.0% |
| PropertyState | 0.0% |
| FICO_Difference | 0.0% |
| EscrowPayment_Flag | 0.0% |
| Flag_Trailing_DaysDiff_GT45 | 0.0% |
| Percent_EDUCATIONAL_ATTAINMENT_Population_25_years_and_over_Bachelors_degree_or_higher | 14.2% |
| Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Mean_household_income_dollars | 14.2% |
| Percent_HOUSING_TENURE_Occupied_housing_units_Owner_occupied | 14.2% |
| Refinanced_3_months_lookahead | 0.0% |

### Flag variance check (F5) — same_window_2026-02

| column | % nonzero | value_counts |
|---|---|---|
| Flag_Trailing_DaysDiff_GT45 | 0.00% | {0: 107764} |
| EscrowPayment_Flag | 0.52% | {0: 107200, 1: 564} |

### Refi base rate + SMOTE ceiling check — same_window_2026-02

| universe | n_loans | n_refi | base_rate | SMOTE ceiling | ratio < ceiling? |
|---|---|---|---|---|---|
| fha | 32956 | 750 | 2.2758% | 0.1 | ratio=0.0233 -> YES |
| conventional | 74806 | 1080 | 1.4437% | 0.2 | ratio=0.0146 -> YES |

### Null rates — production_window_2026-05

| column | null % |
|---|---|
| LoanType | 0.0% |
| CREDIT_BUREAU_PAYMENT_HISTORY | 0.0% |
| PrincipalBalance | 0.0% |
| Is_MailingZip_Equal_PropZip | 0.0% |
| FICO_Score | 0.0% |
| CurrentLTV | 0.0% |
| Login_Count | 65.9% |
| Interest_Delta_Current_Market | 3.1% |
| Ltv_Delta_Orginal_Current | 0.0% |
| PropertyState | 0.0% |
| FICO_Difference | 0.0% |
| EscrowPayment_Flag | 0.0% |
| Flag_Trailing_DaysDiff_GT45 | 0.0% |
| Percent_EDUCATIONAL_ATTAINMENT_Population_25_years_and_over_Bachelors_degree_or_higher | 14.4% |
| Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Mean_household_income_dollars | 14.4% |
| Percent_HOUSING_TENURE_Occupied_housing_units_Owner_occupied | 14.4% |
| Refinanced_3_months_lookahead | 0.0% |

### Flag variance check (F5) — production_window_2026-05

| column | % nonzero | value_counts |
|---|---|---|
| Flag_Trailing_DaysDiff_GT45 | 0.00% | {0: 121493} |
| EscrowPayment_Flag | 0.12% | {0: 121349, 1: 144} |

### Refi base rate + SMOTE ceiling check — production_window_2026-05

| universe | n_loans | n_refi | base_rate | SMOTE ceiling | ratio < ceiling? |
|---|---|---|---|---|---|
| fha | 39984 | 1181 | 2.9537% | 0.1 | ratio=0.0304 -> YES |
| conventional | 81507 | 1613 | 1.9790% | 0.2 | ratio=0.0202 -> YES |

**Note (same_window_2026-02):** `LoanType` values outside both universe buckets, silently excluded from training: {'USDA': 2}
**Note (production_window_2026-05):** `LoanType` values outside both universe buckets, silently excluded from training: {'USDA': 2}

## Figures

- `reports\figures\summary_table.png`
- `reports\figures\null_rates.png`
- `reports\figures\loan_and_refi_counts.png`
- `reports\figures\refi_rates.png`
- `reports\figures\flag_variance.png`
- `reports\figures\feature_percentiles.png`
- `reports\figures\credit_bureau_payment_history_value_counts.png`
- `reports\figures\refi_rate_by_fico.png`
- `reports\figures\refi_rate_by_rate_delta.png`
- `reports\figures\refi_rate_by_ltv.png`
- `reports\figures\property_state_distribution.png`
- `reports\figures\loan_type_breakdown.png`