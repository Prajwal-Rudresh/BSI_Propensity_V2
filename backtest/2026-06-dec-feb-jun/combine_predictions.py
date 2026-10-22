import argparse
import os
from typing import Dict, List, Optional, Tuple

import pandas as pd


def _detect_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Strictly map required columns from input dataframe.

    Returns a mapping from required names to actual dataframe column names:
    {
        "LoanNumber": <col>,
        "Refi_probability": <col>,
        "Propensity Value": <col>,
    }
    """
    # Only allow explicit columns; raise if not present
    columns_set = set(df.columns)

    loan_col: Optional[str] = None
    if "LoanNumber" in columns_set:
        loan_col = "LoanNumber"
    elif "Loan Number" in columns_set:
        loan_col = "Loan Number"

    prob_col: Optional[str] = "pred_prob" if "pred_prob" in columns_set else None
    prop_col: Optional[str] = "y_pred" if "y_pred" in columns_set else None

    missing_required: List[str] = []
    if loan_col is None:
        missing_required.append("LoanNumber (or 'Loan Number')")
    if prob_col is None:
        missing_required.append("pred_prob")
    if prop_col is None:
        missing_required.append("y_pred")

    if missing_required:
        raise ValueError(
            "Missing required input columns: "
            + ", ".join(missing_required)
            + f". Found columns: {list(df.columns)}"
        )

    mapping: Dict[str, str] = {}
    if loan_col:
        mapping["LoanNumber"] = loan_col
    if prob_col:
        mapping["Refi_probability"] = prob_col
    if prop_col:
        mapping["Propensity Value"] = prop_col
    return mapping


def _standardize_df(df: pd.DataFrame) -> pd.DataFrame:
    mapping = _detect_columns(df)
    missing = {"LoanNumber", "Refi_probability", "Propensity Value"} - set(mapping.keys())
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}. Found columns: {list(df.columns)}"
        )

    std = df.rename(columns={v: k for k, v in mapping.items()})[
        ["LoanNumber", "Refi_probability", "Propensity Value"]
    ].copy()

    # Coerce types
    std["LoanNumber"] = std["LoanNumber"].astype(str).str.strip()
    std["Propensity Value"] = pd.to_numeric(std["Propensity Value"], errors="coerce").fillna(0).astype(int)
    std["Refi_probability"] = pd.to_numeric(std["Refi_probability"], errors="coerce").fillna(0.0)
    return std


def _to_percent_if_needed(series: pd.Series) -> pd.Series:
    """
    Convert probabilities to percentage scale if they appear to be in 0-1.
    Heuristic: if max <= 1.0, treat as probability and multiply by 100.
    """
    max_val = series.max(skipna=True)
    if pd.isna(max_val):
        return series
    if max_val <= 1.0:
        return series * 100.0
    return series


def combine_predictions(
    fha_csv: str, conventional_csv: str, output_filename: str
) -> Tuple[str, int]:
    df_fha = pd.read_csv(fha_csv)
    df_conv = pd.read_csv(conventional_csv)

    std_fha = _standardize_df(df_fha)
    std_conv = _standardize_df(df_conv)

    combined = pd.concat([std_fha, std_conv], ignore_index=True)

    # Resolve duplicates by LoanNumber: take max propensity and max probability prior to rules
    aggregated = (
        combined.groupby("LoanNumber", as_index=False)
        .agg({"Propensity Value": "max", "Refi_probability": "max"})
    )

    # Convert to percentage scale if needed
    aggregated["Refi_probability"] = _to_percent_if_needed(aggregated["Refi_probability"])

    # Apply transformations:
    # 1) If propensity == 0 -> probability = 0
    # 2) Where propensity == 1 and probability < 10 -> set to 10
    mask_zero = aggregated["Propensity Value"] == 0
    aggregated.loc[mask_zero, "Refi_probability"] = 0.0

    mask_one_low = (aggregated["Propensity Value"] == 1) & (aggregated["Refi_probability"] < 10.0)
    aggregated.loc[mask_one_low, "Refi_probability"] = 10.0

    # Round for readability
    aggregated["Refi_probability"] = aggregated["Refi_probability"].round(0).astype(int)

    # Convert Propensity Value to YES/NO
    aggregated["Propensity Value"] = aggregated["Propensity Value"].map({0: "NO", 1: "YES"})

    # Ensure column order
    aggregated = aggregated[["LoanNumber", "Refi_probability", "Propensity Value"]]

    # Write output
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    aggregated.to_excel(output_filename, index=False)

    return output_filename, len(aggregated)


def _default_output_path(fha_csv: str, conventional_csv: str) -> str:
    base_dir = os.path.dirname(os.path.commonpath([os.path.abspath(fha_csv), os.path.abspath(conventional_csv)]))
    return os.path.join(base_dir, "combined_predictions.csv")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Combine FHA and Conventional prediction CSVs into one file with columns: "
            "LoanNumber, Refi_probability (in %), Propensity Value (YES or NO)."
        )
    )
    parser.add_argument("--fha", required=True, help="Path to FHA predictions CSV")
    parser.add_argument("--conventional", required=True, help="Path to Conventional predictions CSV")
    parser.add_argument(
        "--output",
        required=False,
        help="Path to write combined CSV. Defaults to sibling 'combined_predictions.csv'",
    )

    args = parser.parse_args()

    output = args.output or _default_output_path(args.fha, args.conventional)
    out_path, n_rows = combine_predictions(args.fha, args.conventional, output)
    print(f"Wrote {n_rows} rows to: {out_path}")


if __name__ == "__main__":
    main()


