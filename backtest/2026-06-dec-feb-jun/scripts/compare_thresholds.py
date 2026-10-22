"""Step 7: compare F12 threshold/override candidates, all chosen without looking at June.

Candidates (leakage-safe -- each decided from training-side data only):
  - current: the existing hardcoded 0.025 + 3 override rules (what's shipped today)
  - best_threshold: the model's own saved best_threshold (training-holdout F2-optimal)
  - target_15pct: a threshold chosen to hit the 2023 design's ~15% flagged target
Each candidate is tried with and without the 3 override rules. June is used only to report
how each pre-decided choice performs, never to select among them.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from evaluate import compute_metrics, load_actuals  # noqa: E402

MODELING_DATA = ROOT / "modeling_data"
BEST_MODEL_DIR = ROOT / "Modeling" / "BestModel"
ACTUALS = [
    ROOT / "data" / "real" / "payoff_reason" / "PayoffReason2026-06.xlsx",
    ROOT / "data" / "real" / "payoff_reason" / "PayoffReason2026-07.xlsx",
    ROOT / "data" / "real" / "payoff_reason" / "PayoffReason2026-08.xlsx",
]
REPORT_PATH = ROOT / "reports" / "threshold_comparison.md"

COMBOS = {
    "fha_same-window": ("final_predictions2026-07_fha_2026-02.csv", "best_model_2026-02_fha.pkl"),
    "fha_production-window": ("final_predictions2026-07_fha_2026-05.csv", "best_model_2026-05_fha.pkl"),
    "conventional_same-window": ("final_predictions2026-07_conventional_2026-02.csv", "best_model_2026-02_conventional.pkl"),
    "conventional_production-window": ("final_predictions2026-07_conventional_2026-05.csv", "best_model_2026-05_conventional.pkl"),
}

CURRENT_THRESHOLD = 0.025
INTEREST_DELTA_CUTOFF = -1
LTV_DELTA_CUTOFF = 25
FICO_DIFF_CUTOFF = 500


def apply_overrides(y_pred: pd.Series, df: pd.DataFrame) -> pd.Series:
    y_pred = y_pred.copy()
    y_pred = y_pred.where(~((df["Interest_Delta_Current_Market"] < INTEREST_DELTA_CUTOFF) & (y_pred == 1)), 0)
    y_pred = y_pred.where(~((df["Ltv_Delta_Orginal_Current"] > LTV_DELTA_CUTOFF) & (y_pred == 0)), 1)
    y_pred = y_pred.where(~((df["FICO_Difference"] > FICO_DIFF_CUTOFF) & (y_pred == 0)), 1)
    return y_pred


def main() -> None:
    refi_loan_numbers = load_actuals(ACTUALS)
    lines = ["# Step 7: threshold/override comparison (aggregate-only)", ""]

    for combo, (scored_file, model_file) in COMBOS.items():
        df = pd.read_csv(MODELING_DATA / scored_file, dtype={"LoanNumber": str})
        saved = joblib.load(BEST_MODEL_DIR / model_file)  # trusted, locally-trained this session
        best_threshold = saved["best_threshold"]
        target_threshold = saved["threshold_target_pct_flagged"]

        candidates = {
            "current (0.025)": CURRENT_THRESHOLD,
            f"best_threshold ({best_threshold:.4f})": best_threshold,
            f"target_15pct ({target_threshold:.4f})": target_threshold,
        }

        lines.append(f"## {combo}")
        lines.append("")
        lines.append("| threshold candidate | overrides | n_flagged | %flagged | recall | precision | auc | ks |")
        lines.append("|---|---|---|---|---|---|---|---|")

        for cand_label, thr in candidates.items():
            for use_overrides in (False, True):
                y_pred_base = (df["pred_prob"] >= thr).astype(int)
                y_pred = apply_overrides(y_pred_base, df) if use_overrides else y_pred_base
                scored = df[["LoanNumber", "pred_prob"]].copy()
                scored["y_pred"] = y_pred
                metrics = compute_metrics(scored, refi_loan_numbers)
                lines.append(
                    f"| {cand_label} | {'with' if use_overrides else 'without'} | "
                    f"{metrics['n_flagged']} | {metrics['pct_flagged']:.4%} | "
                    f"{metrics['recall']:.4%} | {metrics['precision']:.4%} | "
                    f"{metrics['auc']:.4f} | {metrics['ks']:.4f} |"
                )
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
