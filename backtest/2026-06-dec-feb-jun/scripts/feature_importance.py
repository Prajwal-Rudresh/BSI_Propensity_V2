"""Feature importance from the final (all-fixes-applied, seeded) models.

Aggregate only: feature names + importance scores, nothing loan-level.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BEST_MODEL_DIR = ROOT / "Modeling" / "BestModel"
FIGURES_DIR = ROOT / "reports" / "figures"
REPORT_PATH = ROOT / "reports" / "feature_importance.md"

MODELS = {
    "fha_same-window": "best_model_2026-02_fha.pkl",
    "fha_production-window": "best_model_2026-05_fha.pkl",
    "conventional_same-window": "best_model_2026-02_conventional.pkl",
    "conventional_production-window": "best_model_2026-05_conventional.pkl",
}


def load_importance(path: Path) -> pd.Series:
    saved = joblib.load(path)  # trusted, locally-trained artifact from this same session
    model = saved["model"]
    columns = saved["feature_columns"]
    importances = model.feature_importances_
    return pd.Series(importances, index=columns).sort_values(ascending=False)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    all_importances: dict[str, pd.Series] = {}
    for label, filename in MODELS.items():
        path = BEST_MODEL_DIR / filename
        if not path.exists():
            print(f"Missing: {path}")
            continue
        all_importances[label] = load_importance(path)

    lines = ["# Feature importance (aggregate scores only, final models)", ""]
    for label, importances in all_importances.items():
        lines.append(f"## {label}")
        lines.append("")
        lines.append("| feature | importance |")
        lines.append("|---|---|")
        for feat, val in importances.head(15).items():
            lines.append(f"| {feat} | {val} |")
        lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")

    # One combined chart: top 12 features per model, side by side
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    for ax, (label, importances) in zip(axes.flat, all_importances.items()):
        top = importances.head(12).sort_values()
        ax.barh(top.index, top.values, color="tab:blue")
        ax.set_title(label, fontsize=10)
        ax.tick_params(labelsize=7)
    fig.suptitle("Top 12 feature importances per model (final, all fixes applied)")
    fig.tight_layout()
    out = FIGURES_DIR / "feature_importance.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
