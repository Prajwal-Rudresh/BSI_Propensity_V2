# Backtest: Dec 2025-Feb 2026 Train / Jun 2026 Test

Self-contained, isolated copy of the pipeline for the model-improvement backtest described in
`backtest-plan.md`. Per `CLAUDE.md`'s "improved model stays on its own branch or folder" rule:

- `Modeling/`, `data_preperation/`, `modeling_data/`, `app.py`, `combine_predictions.py`,
  `templates/`, `requirements.txt` are **copies** of the repo-root pipeline, as of the commit this
  folder was created from. Root is the untouched reference for the separate engineering-quality
  track (see root `CLAUDE.md`) — all defect fixes and model changes for this backtest happen only
  in this folder's copies.
- `data/real/` — real input data for this backtest, git-ignored, never opened/read/printed by
  Claude (see `data/real/README.md`, `data/real/MANIFEST.md`). **Real data only** — no synthetic
  data is used anywhere in this track.
- Nothing in this folder is merged into root or delivered to production without Anwar's sign-off.

See `backtest-plan.md` for the experiment design and `../../docs/context/known-findings.md`
(F1-F28) for the defects being fixed here.
