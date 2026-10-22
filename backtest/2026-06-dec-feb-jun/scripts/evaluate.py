"""Read-only evaluation harness for the Dec'25-Feb'26/Jun'26 backtest.

Computes Recall, the legacy "Specificity" (kept as-is = % flagged), Precision,
AUC, KS, and % flagged for a scored file against one or more PayoffReason
actuals files. Per-universe. Outputs an aggregate metrics report only --
never loan-level rows.

Scored-file contract (matches project-background.md's "Columns in the
production files"): must have `LoanNumber`, `pred_prob`, `y_pred`.

Actuals-file contract (matches ModelInference.py's monthly label file):
PayoffReason{YYYY-MM}.xlsx with a `Loan Number` column and a `Refi` Yes/No
column. A loan is an actual refi if it appears with Refi == "Yes" in ANY of
the actuals files passed in (June+July+August, per backtest-plan.md).

Usage:
    python evaluate.py --scored scored_conventional.csv \
        --actuals data/real/payoff_reason/PayoffReason2026-06.xlsx \
                  data/real/payoff_reason/PayoffReason2026-07.xlsx \
                  data/real/payoff_reason/PayoffReason2026-08.xlsx \
        --universe conventional --out reports/eval_conventional.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def _normalize_loan_number(series: pd.Series) -> pd.Series:
    """Loan numbers as strings everywhere (CLAUDE.md code standard; also F19)."""
    return series.astype(str).str.strip().str.lstrip("0").replace("", "0")


def load_scored(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_excel(path)
    required = {"LoanNumber", "pred_prob", "y_pred"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"scored file {path} missing columns: {missing}")
    df = df[["LoanNumber", "pred_prob", "y_pred"]].copy()
    df["LoanNumber"] = _normalize_loan_number(df["LoanNumber"])
    return df


def load_actuals(paths: list[Path]) -> pd.Series:
    """Returns a Series indexed by normalized LoanNumber, value 1 if any file
    marks that loan Refi == Yes, else not present (treated as 0 downstream)."""
    refi_loan_numbers: set[str] = set()
    for p in paths:
        df = pd.read_excel(p)
        loan_col = "Loan Number" if "Loan Number" in df.columns else "LoanNumber"
        refi_col = "Refi" if "Refi" in df.columns else None
        if refi_col is None:
            raise ValueError(f"actuals file {p} has no 'Refi' column; columns: {list(df.columns)}")
        loans = _normalize_loan_number(df[loan_col])
        is_yes = df[refi_col].astype(str).str.strip().str.lower() == "yes"
        refi_loan_numbers.update(loans[is_yes].tolist())
    return refi_loan_numbers


def ks_statistic(pred_prob: np.ndarray, actual: np.ndarray) -> float:
    """Max gap between cumulative score distributions of refis vs non-refis."""
    pos = np.sort(pred_prob[actual == 1])
    neg = np.sort(pred_prob[actual == 0])
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    grid = np.sort(np.unique(np.concatenate([pos, neg])))
    cdf_pos = np.searchsorted(pos, grid, side="right") / len(pos)
    cdf_neg = np.searchsorted(neg, grid, side="right") / len(neg)
    return float(np.max(np.abs(cdf_pos - cdf_neg)))


def compute_metrics(scored: pd.DataFrame, refi_loan_numbers: set[str]) -> dict:
    scored = scored.copy()
    scored["actual_refi"] = scored["LoanNumber"].isin(refi_loan_numbers).astype(int)

    y_true = scored["actual_refi"].to_numpy()
    y_pred = scored["y_pred"].astype(int).to_numpy()
    pred_prob = scored["pred_prob"].astype(float).to_numpy()

    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    n = len(scored)
    n_flagged = int((y_pred == 1).sum())
    assert n == tp + fp + fn + tn, "confusion matrix doesn't sum to total rows"

    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    pct_flagged = n_flagged / n if n > 0 else float("nan")
    # F3 / legacy "Specificity": (TP+FP)/(TN+TP+FP+FN), i.e. % of loans flagged "Yes" --
    # NOT the textbook TN/(TN+FP). Kept exactly as the legacy tool defines it (hard rule #3).
    legacy_specificity = (tp + fp) / (tn + tp + fp + fn) if n > 0 else float("nan")
    true_specificity = tn / (tn + fp) if (tn + fp) > 0 else float("nan")  # reference only
    assert abs(legacy_specificity - pct_flagged) < 1e-9, "legacy specificity should equal %flagged"

    auc = roc_auc_score(y_true, pred_prob) if len(set(y_true.tolist())) > 1 else float("nan")
    ks = ks_statistic(pred_prob, y_true)

    return {
        "n_loans": n,
        "n_actual_refi": int(y_true.sum()),
        "n_flagged": n_flagged,
        "pct_flagged": pct_flagged,
        "recall": recall,
        "precision": precision,
        "legacy_specificity": legacy_specificity,
        "true_specificity_TN_over_TN_plus_FP": true_specificity,
        "auc": auc,
        "ks": ks,
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scored", required=True, type=Path)
    ap.add_argument("--actuals", required=True, nargs="+", type=Path)
    ap.add_argument("--universe", required=True)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    scored = load_scored(args.scored)
    refi_loan_numbers = load_actuals(args.actuals)
    metrics = compute_metrics(scored, refi_loan_numbers)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    cm = metrics["confusion_matrix"]
    lines = [
        f"# Evaluation: {args.universe}",
        "",
        f"- scored file: `{args.scored.name}`",
        f"- actuals files: {[p.name for p in args.actuals]}",
        "",
        "## Confusion matrix",
        "",
        "|  | Actual refi | Actual no-refi |",
        "|---|---|---|",
        f"| **Flagged Yes** | TP = {cm['tp']} | FP = {cm['fp']} |",
        f"| **Flagged No** | FN = {cm['fn']} | TN = {cm['tn']} |",
        "",
        "## Metrics",
        "",
        "| metric | value |",
        "|---|---|",
    ]
    for k, v in metrics.items():
        if k == "confusion_matrix":
            continue
        lines.append(f"| {k} | {v} |")
    args.out.write_text("\n".join(lines), encoding="utf-8")
    args.out.with_suffix(".json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
