"""Step 8 centerpiece: the honest before/after comparison.

BEFORE = Step 4's baseline: the truly unmodified legacy pipeline (all bugs intact:
  F19/F7 typing issues, F5's dead flag, F14/F22's frozen 2023 rate date, unseeded Optuna),
  scored with the original hardcoded 0.025 threshold + 3 override rules.
AFTER  = the fully-fixed pipeline (F19, F7, F5, F14/F22, F27, F15 all applied) scored with
  the recommended F12 candidate: the model's own training-holdout best_threshold + the
  same 3 override rules (chosen without ever looking at June -- see compare_thresholds.py).

Both computed by the identical evaluate.py harness against the identical June+July+August
2026 actuals. Aggregate-only throughout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from evaluate import compute_metrics, load_actuals  # noqa: E402

MODELING_DATA = ROOT / "modeling_data"
BEST_MODEL_DIR = ROOT / "Modeling" / "BestModel"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
ACTUALS = [
    ROOT / "data" / "real" / "payoff_reason" / "PayoffReason2026-06.xlsx",
    ROOT / "data" / "real" / "payoff_reason" / "PayoffReason2026-07.xlsx",
    ROOT / "data" / "real" / "payoff_reason" / "PayoffReason2026-08.xlsx",
]

COMBOS = {
    "fha_same-window": {
        "before_json": "eval_fha_same-window_before.json",
        "scored_file": "final_predictions2026-07_fha_2026-02.csv",
        "model_file": "best_model_2026-02_fha.pkl",
    },
    "fha_production-window": {
        "before_json": "eval_fha_production-window_before.json",
        "scored_file": "final_predictions2026-07_fha_2026-05.csv",
        "model_file": "best_model_2026-05_fha.pkl",
    },
    "conventional_same-window": {
        "before_json": "eval_conventional_same-window_before.json",
        "scored_file": "final_predictions2026-07_conventional_2026-02.csv",
        "model_file": "best_model_2026-02_conventional.pkl",
    },
    "conventional_production-window": {
        "before_json": "eval_conventional_production-window_before.json",
        "scored_file": "final_predictions2026-07_conventional_2026-05.csv",
        "model_file": "best_model_2026-05_conventional.pkl",
    },
}

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
    results: dict[str, dict] = {}

    for combo, paths in COMBOS.items():
        before = json.loads((REPORTS_DIR / paths["before_json"]).read_text())

        df = pd.read_csv(MODELING_DATA / paths["scored_file"], dtype={"LoanNumber": str})
        saved = joblib.load(BEST_MODEL_DIR / paths["model_file"])  # trusted, locally-trained
        best_threshold = saved["best_threshold"]
        y_pred_base = (df["pred_prob"] >= best_threshold).astype(int)
        y_pred = apply_overrides(y_pred_base, df)
        scored = df[["LoanNumber", "pred_prob"]].copy()
        scored["y_pred"] = y_pred
        after = compute_metrics(scored, refi_loan_numbers)
        after["threshold_used"] = best_threshold

        results[combo] = {"before": before, "after": after}

    lines = ["# Step 8: Final before/after comparison", "", "Both sides: identical `evaluate.py` harness, identical June+July+August 2026 actuals.", ""]
    for combo, r in results.items():
        b, a = r["before"], r["after"]
        lines.append(f"## {combo}")
        lines.append("")
        lines.append("| metric | before (original, 0.025+overrides) | after (fixed, best_threshold+overrides) | delta |")
        lines.append("|---|---|---|---|")
        for key, fmt in [
            ("recall", "{:.2%}"), ("precision", "{:.4%}"), ("pct_flagged", "{:.2%}"),
            ("legacy_specificity", "{:.2%}"), ("auc", "{:.4f}"), ("ks", "{:.4f}"),
        ]:
            bv, av = b[key], a[key]
            delta = av - bv
            lines.append(f"| {key} | {fmt.format(bv)} | {fmt.format(av)} | {delta:+.4f} |")
        cm_b, cm_a = b["confusion_matrix"], a["confusion_matrix"]
        lines.append(f"| confusion matrix (TP/FP/FN/TN) | {cm_b['tp']}/{cm_b['fp']}/{cm_b['fn']}/{cm_b['tn']} | {cm_a['tp']}/{cm_a['fp']}/{cm_a['fn']}/{cm_a['tn']} | - |")
        lines.append(f"| threshold used | 0.025 | {a['threshold_used']:.4f} | - |")
        lines.append("")

    (REPORTS_DIR / "final_before_after.md").write_text("\n".join(lines), encoding="utf-8")
    (REPORTS_DIR / "final_before_after.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {REPORTS_DIR / 'final_before_after.md'}")

    # Chart: precision and recall, before vs after, all 4 combos
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    combos = list(results.keys())
    x = range(len(combos))
    width = 0.35
    for ax, metric, fmt_pct in [(axes[0], "recall", True), (axes[1], "precision", True)]:
        before_vals = [results[c]["before"][metric] * 100 for c in combos]
        after_vals = [results[c]["after"][metric] * 100 for c in combos]
        ax.bar([p - width / 2 for p in x], before_vals, width=width, label="before", color="tab:gray")
        ax.bar([p + width / 2 for p in x], after_vals, width=width, label="after", color="tab:green")
        ax.set_xticks(list(x))
        ax.set_xticklabels(combos, rotation=20, fontsize=8)
        ax.set_ylabel(f"{metric} %")
        ax.set_title(metric.capitalize())
        ax.legend()
    fig.suptitle("Final before/after: original (0.025+overrides) vs fixed (best_threshold+overrides)")
    fig.tight_layout()
    out = FIGURES_DIR / "final_before_after.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
