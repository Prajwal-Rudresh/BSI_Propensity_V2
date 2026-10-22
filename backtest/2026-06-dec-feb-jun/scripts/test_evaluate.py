"""Unit tests for evaluate.py's metric math (hand-computed numbers, no data files).

Run: python -m pytest backtest/2026-06-dec-feb-jun/scripts/test_evaluate.py -q
"""
import numpy as np
import pandas as pd

from evaluate import compute_metrics, ks_statistic


def test_compute_metrics_matches_hand_calculation():
    # 10 loans: 3 actual refis (loan numbers 1,2,3), 2 flagged Yes (1,4).
    # TP=1 (loan 1), FP=1 (loan 4), FN=2 (loans 2,3), TN=6.
    scored = pd.DataFrame({
        "LoanNumber": [str(i) for i in range(1, 11)],
        "pred_prob": [0.9, 0.8, 0.7, 0.6, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        "y_pred": [1, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    })
    refi_loan_numbers = {"1", "2", "3"}

    m = compute_metrics(scored, refi_loan_numbers)
    cm = m["confusion_matrix"]

    assert cm == {"tp": 1, "fp": 1, "fn": 2, "tn": 6}
    assert m["n_flagged"] == 2
    assert m["pct_flagged"] == 2 / 10
    # F3 / confirmed legacy formula: Specificity = (TP+FP) / (TN+TP+FP+FN)
    assert m["legacy_specificity"] == (1 + 1) / (6 + 1 + 1 + 2) == 2 / 10
    assert m["true_specificity_TN_over_TN_plus_FP"] == 6 / (6 + 1)
    assert m["recall"] == 1 / 3
    assert m["precision"] == 1 / 2


def test_ks_statistic_perfect_separation_is_one():
    pred_prob = np.array([0.9, 0.8, 0.7, 0.1, 0.2, 0.3])
    actual = np.array([1, 1, 1, 0, 0, 0])
    assert ks_statistic(pred_prob, actual) == 1.0


def test_ks_statistic_no_separation_is_near_zero():
    pred_prob = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    actual = np.array([1, 0, 1, 0, 1, 0])
    assert ks_statistic(pred_prob, actual) == 0.0
