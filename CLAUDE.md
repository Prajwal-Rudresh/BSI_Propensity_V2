# PG Score — Claude Code Context

You are helping Prajwal (Product Management intern, BSI Financial Services) take over, fix and
harden the existing **Portfolio Guardian (PG) Score** codebase. PG is a monthly refinance-propensity
model for BSI's serviced mortgage portfolio.

**The goal of this repo is engineering quality, not a new model.** Same model, same algorithm,
same features, same training window, same cutoff. We fix code defects, add tests, restructure the
code, and make the process reproducible and auditable.

Detailed context lives in these files — read the relevant one before starting a task:

- @docs/context/project-background.md — what PG is, the monthly process, inputs, features, label
- @docs/context/known-findings.md — confirmed defects and open questions (from the Aug 2026 audit)
- @docs/context/scope-and-change-policy.md — what is in/out of scope and what needs sign-off
- @docs/context/glossary.md — BSI and domain terms
- @backtest/2026-06-dec-feb-jun/backtest-plan.md — Dec'25-Feb'26 train / Jun'26 test backtest
  experiment (isolated folder: its own `data/real/` + `data/synthetic/`, never merged/delivered
  without Anwar sign-off, per the "improved model stays on its own branch or folder" rule)

---

## Hard rules (never break these)

1. **No real borrower data in prompts, code, tests, fixtures, commits or docs.** Loan numbers,
   FICO, credit bureau data, balances, addresses — none of it. Use `data/synthetic/` only.
   Do not open, read, print, `head`, or summarize anything in `data/real/`, `outputs/`, `*.xlsx`,
   `*.csv` outside `data/synthetic/`, or `*.pkl`. If a task seems to need real data, stop and ask.
2. **Never change model behavior without explicit instruction.** No new features, no feature
   removal, no threshold/cutoff change, no calibration, no algorithm change, no change to the
   12-month training window, no change to WoE binning logic.
3. **Keep the existing Specificity formula exactly as it is.** It is known to return the share of
   loans flagged "Yes" rather than TN/(TN+FP). That is documented, not fixed. Do not "correct" it.
4. **New metrics are additive only.** Precision, AUC, KS and % flagged are added as new outputs
   next to the existing ones. Never rename, remove or reorder existing report columns.
5. **Never edit golden-master files** (`tests/golden/`) to make a test pass. If the golden test
   fails, the code is wrong until proven otherwise. Report the diff and stop.
6. **Fixes marked `needs-signoff` change delivered scores.** Implement them only on a branch,
   produce a before/after diff, and do not merge. See scope-and-change-policy.md.
7. **No secrets in code.** Credentials come from environment variables (`.env` is git-ignored).
   Never hardcode connection strings, keys, hostnames with credentials, or tokens.
8. **Do not guess.** If something in the legacy code is ambiguous (a cutoff value, a join key, a
   date rule), say so and list the options. Facts we have not confirmed are listed under
   "Open questions" in known-findings.md — do not treat them as settled.

---

## How to work

- **Plan first.** For any change beyond a one-liner, propose a plan (files touched, tests added,
  expected effect on outputs) and wait for approval before editing.
- **One issue → one branch → one small PR.** Branch names: `fix/<issue#>-short-name`,
  `refactor/<issue#>-short-name`, `test/...`, `docs/...`.
- **Test first for defects.** Write a failing test that reproduces the defect, then fix it.
- **Behavior-preserving refactors.** Every refactor must leave `make golden` output identical.
  State explicitly in the PR description: "Golden master: unchanged" or "Golden master: changed
  (needs-signoff, see diff)".
- **Explain every change in plain language.** Prajwal must be able to explain each diff to the
  model owner without you in the room. Prefer small, readable code over clever code.
- **Cite file and line** when describing existing behavior.

## Code standards

- Python 3.x matching the pinned version in `requirements.lock` (match the legacy EC2 versions
  first — a `.pkl` saved under one scikit-learn version may load wrongly under another).
- Type hints on all new/refactored functions; `ruff` clean; `mypy` clean on `pg_score/`.
- Pure functions for features and metrics (input DataFrame → output Series/DataFrame, no I/O).
- All merges must assert expected row counts or use `validate=` (e.g. `"one_to_one"`).
- Loan numbers are **strings**, never floats/ints (leading zeros, join safety).
- No bare `except`. Fail loudly with a clear message; never silently `fillna`/`dropna` without a
  logged count and a comment explaining why.
- Seed every source of randomness from config.
- Structured logging via `logging`, no `print` in library code.
- SQL is parameterized, never built by string concatenation.

## Commands

```bash
make setup       # create venv, install pinned deps, install pre-commit hooks
make lint        # ruff
make typecheck   # mypy
make test        # pytest on synthetic data (unit, contract, invariant, regression)
make e2e         # full pipeline end-to-end on synthetic data
make security    # bandit + gitleaks
make synthetic   # regenerate synthetic data in data/synthetic/
make golden      # BSI machine ONLY: reproduce Aug 2026 against real data, compare to golden hashes
```

Run `make lint typecheck test` before proposing any PR. Never run `make golden` yourself unless
Prajwal says the environment is the approved BSI machine.

## Repo layout

```
# The original Flowise export is preserved at git tag `v0-flowise-original` (not a live
# directory). The files below (Modeling/, data_preperation/, modeling_data/, app.py, etc. at
# repo root) ARE that export, now the live working copy we edit directly.
pg_score/          # refactored package (built up in phases)
  config/          # run month, cutoff, paths, universes (YAML)
  ingest/          # load the 6 inputs; parameterized SQL
  validate/        # data-contract checks (fail loud)
  features/        # one pure function per feature
  train/  score/   # same algorithm, window, cutoff as legacy
  evaluate/        # existing metrics (unchanged) + new metrics (additive)
  registry/        # versioned model save/load + run manifest
  report/          # same monthly report + new metric columns
  run.py           # entry point: --universe {conventional,fha} --run-month YYYY-MM
tests/
  unit/ contract/ invariants/ regression/ e2e/
  golden/          # hashes + summary metrics ONLY (no borrower data). Do not edit.
data/
  synthetic/       # safe fake data — the only data you may read
  real/            # git-ignored, BSI machine only — never read
docs/
  context/         # files referenced above
  adr/             # architecture decision records
scripts/
```

## Current phase

Update this line as work progresses:

**Phase: Step 1 — Setup. Legacy code being exported from Flowise. No refactoring yet.**

Phases: 1 Setup → 2 Map the current system → 3 Reproduce Aug 2026 (golden master) → 4 Code review →
5 Safety-net tests → 6 Defect fixes → 7 Refactor → 8 CI (GitHub Actions, later Azure DevOps) →
9 Process + docs → 10 Prove it + Azure DevOps migration.
