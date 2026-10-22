"""Full EDA pass (aggregate-only) before any model training.

Covers: per-feature null rates, loan-number dtype audit, refi base rate per
universe/window vs SMOTE's sampling_strategy ceiling (F15), and whether
payoff_data is already refi-only (F18/F25). Writes one report file, no
row-level content.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_REAL = ROOT / "data" / "real"
MODELING_DATA = ROOT / "modeling_data"
REPORT_PATH = ROOT / "reports" / "eda.md"
FIGURES_DIR = ROOT / "reports" / "figures"

# Continuous features we chart with percentile summaries only (p1/p25/median/p75/p99) --
# never a raw histogram, so no single bin/extreme value can expose one loan's data.
CONTINUOUS_FEATURES = ["PrincipalBalance", "FICO_Score", "CurrentLTV", "Interest_Delta_Current_Market"]

# CREDIT_BUREAU_PAYMENT_HISTORY is a categorical rating code (0-6, D, B, .), not continuous --
# confirmed via dtype + nunique while building this script. Charted as value-counts instead
# (only ~10 categories across 100K+ loans, safe aggregate).
CATEGORICAL_FEATURES = ["CREDIT_BUREAU_PAYMENT_HISTORY"]

FEATURE_COLUMNS = [
    "LoanType", "CREDIT_BUREAU_PAYMENT_HISTORY", "PrincipalBalance",
    "Is_MailingZip_Equal_PropZip", "FICO_Score", "CurrentLTV", "Login_Count",
    "Interest_Delta_Current_Market", "Ltv_Delta_Orginal_Current", "PropertyState",
    "FICO_Difference", "EscrowPayment_Flag", "Flag_Trailing_DaysDiff_GT45",
    "Percent_EDUCATIONAL_ATTAINMENT_Population_25_years_and_over_Bachelors_degree_or_higher",
    "Estimate_INCOME_AND_BENEFITS_IN_2021_INFLATION_ADJUSTED_DOLLARS_Total_households_Mean_household_income_dollars",
    "Percent_HOUSING_TENURE_Occupied_housing_units_Owner_occupied",
    "Refinanced_3_months_lookahead",
]

UNIVERSE_BUCKETS = {
    "fha": ["FHA", "VA"],
    "conventional": ["CONVENTIONAL", "PMI"],
}
SMOTE_CEILING = {"fha": 0.1, "conventional": 0.2}

WINDOWS = {
    "same_window_2026-02": MODELING_DATA / "training_data_2026-02.csv",
    "production_window_2026-05": MODELING_DATA / "training_data_2026-05.csv",
}


def null_rates(df: pd.DataFrame) -> dict:
    return {col: (df[col].isna().mean() * 100 if col in df.columns else None)
            for col in FEATURE_COLUMNS}


def null_rate_report(rates: dict, label: str) -> list[str]:
    lines = [f"### Null rates — {label}", "", "| column | null % |", "|---|---|"]
    for col, pct in rates.items():
        lines.append(f"| {col} | {'MISSING FROM FILE' if pct is None else f'{pct:.1f}%'} |")
    lines.append("")
    return lines


def refi_rates(df: pd.DataFrame) -> dict:
    out = {}
    for universe, bucket in UNIVERSE_BUCKETS.items():
        sub = df[df["LoanType"].isin(bucket)]
        n = len(sub)
        if n == 0:
            out[universe] = None
            continue
        n_refi = int(sub["Refinanced_3_months_lookahead"].astype(int).sum())
        n_non_refi = n - n_refi
        ratio = n_refi / n_non_refi if n_non_refi > 0 else float("inf")
        out[universe] = {
            "n": n, "n_refi": n_refi, "base_rate": n_refi / n, "ratio": ratio,
            "ceiling": SMOTE_CEILING[universe],
        }
    return out


def refi_rate_report(rates: dict, label: str) -> list[str]:
    lines = [f"### Refi base rate + SMOTE ceiling check — {label}", "",
             "| universe | n_loans | n_refi | base_rate | SMOTE ceiling | ratio < ceiling? |",
             "|---|---|---|---|---|---|"]
    for universe, r in rates.items():
        if r is None:
            lines.append(f"| {universe} | 0 | - | - | - | n/a (no rows) |")
            continue
        ok = "YES" if r["ratio"] < r["ceiling"] else "NO -- WOULD CRASH SMOTE (F15)"
        lines.append(
            f"| {universe} | {r['n']} | {r['n_refi']} | {r['base_rate']:.4%} | {r['ceiling']} | "
            f"ratio={r['ratio']:.4f} -> {ok} |"
        )
    lines.append("")
    return lines


def percentile_summary(df: pd.DataFrame) -> dict:
    """p1/p25/median/p75/p99 only -- never min/max/raw histogram, so no single
    extreme loan's value is ever shown."""
    out = {}
    for col in CONTINUOUS_FEATURES:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) < 20:  # too few points to safely summarize in aggregate
            continue
        out[col] = s.quantile([0.01, 0.25, 0.5, 0.75, 0.99]).to_dict()
    return out


def dtype_audit() -> list[str]:
    lines = ["### Loan-number dtype audit (F19)", "", "| file | column | dtype |", "|---|---|---|"]
    checks = [
        (DATA_REAL / "one_off" / "one_off_trimmed_2025-07_2026-06.csv", "LoanNumber"),
        (DATA_REAL / "mlw_logins" / "mlw_logins_trimmed_2025-12_2026-06.csv", "LoanNumber"),
        (DATA_REAL / "credit_bureau" / "Credit Bureau Data.csv", "ACCT_NBR"),
        (DATA_REAL / "payoff_data" / "Combined_Payoff_Data_with_RefinanceYes.xlsx", "LoanNumber"),
    ]
    for path, col in checks:
        try:
            if path.suffix.lower() == ".csv":
                # Full-file scan, not just a head sample -- a CSV can have the dtype shift
                # partway through (e.g. a later chunk containing a non-numeric value), which
                # a nrows=5000 sample would silently miss.
                dtypes_seen = set()
                for chunk in pd.read_csv(path, usecols=[col], chunksize=500_000):
                    dtypes_seen.add(str(chunk[col].dtype))
                dtype_str = dtypes_seen.pop() if len(dtypes_seen) == 1 else f"MIXED: {dtypes_seen}"
            else:
                head = pd.read_excel(path, usecols=[col])
                dtype_str = str(head[col].dtype)
            lines.append(f"| {path.name} | {col} | {dtype_str} |")
        except Exception as e:  # noqa: BLE001
            lines.append(f"| {path.name} | {col} | ERROR: {type(e).__name__}: {e} |")
    lines.append("")
    return lines


FLAG_COLUMNS = ("Flag_Trailing_DaysDiff_GT45", "EscrowPayment_Flag")


def flag_variance(df: pd.DataFrame) -> dict:
    """F5/EscrowPayment_Flag: checks VALUE variance, not nullness -- a column can be
    0% null and still always be the literal value 0 (F5's actual defect)."""
    out = {}
    for col in FLAG_COLUMNS:
        if col not in df.columns:
            out[col] = None
            continue
        out[col] = {
            "pct_nonzero": (df[col] != 0).mean() * 100,
            "value_counts": df[col].value_counts(dropna=False).to_dict(),
        }
    return out


def flag_variance_report(flags: dict, label: str) -> list[str]:
    lines = [f"### Flag variance check (F5) — {label}", "",
             "| column | % nonzero | value_counts |", "|---|---|---|"]
    for col, v in flags.items():
        if v is None:
            lines.append(f"| {col} | MISSING | - |")
        else:
            lines.append(f"| {col} | {v['pct_nonzero']:.2f}% | {v['value_counts']} |")
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Plots -- every plot is built from the same aggregate numbers already written
# to eda.md above, nothing re-reads row-level data here.
# ---------------------------------------------------------------------------

def plot_null_rates(all_rates: dict[str, dict]) -> Path:
    cols = [c for c in FEATURE_COLUMNS if any(all_rates[w].get(c) is not None for w in all_rates)]
    fig, ax = plt.subplots(figsize=(10, max(4, 0.35 * len(cols))))
    width = 0.35
    y = range(len(cols))
    for i, (label, rates) in enumerate(all_rates.items()):
        vals = [rates.get(c) or 0 for c in cols]
        ax.barh([p + i * width for p in y], vals, height=width, label=label)
    ax.set_yticks([p + width / 2 for p in y])
    ax.set_yticklabels(cols, fontsize=8)
    ax.set_xlabel("null %")
    ax.set_title("Feature null rates by window")
    ax.legend()
    fig.tight_layout()
    out = FIGURES_DIR / "null_rates.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def plot_loan_and_refi_counts(all_refi: dict[str, dict]) -> Path:
    """Simple side-by-side counts: how many loans, how many of them refi'd --
    per universe, per window. Companion to the % rate chart."""
    windows = list(all_refi.keys())
    universes = list(UNIVERSE_BUCKETS.keys())
    colors = {"fha": "tab:blue", "conventional": "tab:orange"}

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    width = 0.35
    x = range(len(windows))

    for universe_i, universe in enumerate(universes):
        totals = [(all_refi[w][universe]["n"] if all_refi[w].get(universe) else 0) for w in windows]
        refis = [(all_refi[w][universe]["n_refi"] if all_refi[w].get(universe) else 0) for w in windows]
        offset = (universe_i - 0.5) * width
        axes[0].bar([p + offset for p in x], totals, width=width, label=universe,
                    color=colors[universe])
        axes[1].bar([p + offset for p in x], refis, width=width, label=universe,
                    color=colors[universe])

    axes[0].set_title("Total loans")
    axes[1].set_title("Loans that refinanced")
    for ax in axes:
        ax.set_xticks(list(x))
        ax.set_xticklabels(windows, fontsize=8)
        ax.legend(fontsize=8)
    fig.suptitle("Loan counts by universe and window")
    fig.tight_layout()
    out = FIGURES_DIR / "loan_and_refi_counts.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def plot_refi_rates(all_refi: dict[str, dict]) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4))
    windows = list(all_refi.keys())
    universes = list(UNIVERSE_BUCKETS.keys())
    width = 0.35
    x = range(len(windows))
    colors = {"fha": "tab:blue", "conventional": "tab:orange"}
    for i, universe in enumerate(universes):
        base_rates = [
            (all_refi[w][universe]["base_rate"] * 100 if all_refi[w].get(universe) else 0)
            for w in windows
        ]
        ax.bar([p + i * width for p in x], base_rates, width=width, label=universe,
               color=colors[universe])
        ceiling_pct = SMOTE_CEILING[universe] / (1 + SMOTE_CEILING[universe]) * 100
        ax.axhline(ceiling_pct, linestyle="--", linewidth=1.5, color=colors[universe],
                   label=f"{universe} SMOTE ceiling ({ceiling_pct:.1f}%)")
    ax.set_xticks([p + width / 2 for p in x])
    ax.set_xticklabels(windows)
    ax.set_ylabel("refi base rate %")
    ax.set_title("Refi base rate vs SMOTE sampling_strategy ceiling (F15)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    out = FIGURES_DIR / "refi_rates.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def plot_flag_variance(all_flags: dict[str, dict]) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4))
    windows = list(all_flags.keys())
    width = 0.35
    x = range(len(windows))
    for i, col in enumerate(FLAG_COLUMNS):
        vals = [(all_flags[w][col]["pct_nonzero"] if all_flags[w].get(col) else 0) for w in windows]
        ax.bar([p + i * width for p in x], vals, width=width, label=col)
    ax.set_xticks([p + width / 2 for p in x])
    ax.set_xticklabels(windows)
    ax.set_ylabel("% nonzero")
    ax.set_title("Flag variance check (F5): Flag_Trailing_DaysDiff_GT45 vs EscrowPayment_Flag")
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = FIGURES_DIR / "flag_variance.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def plot_feature_percentiles(all_percentiles: dict[str, dict]) -> Path:
    n = len(CONTINUOUS_FEATURES)
    fig, axes = plt.subplots(1, n, figsize=(3.2 * n, 4))
    if n == 1:
        axes = [axes]
    for ax, col in zip(axes, CONTINUOUS_FEATURES):
        for label, percentiles in all_percentiles.items():
            if col not in percentiles:
                continue
            p = percentiles[col]
            xs = [0.01, 0.25, 0.5, 0.75, 0.99]
            ys = [p[x] for x in xs]
            ax.plot(ys, xs, marker="o", label=label)
        ax.set_title(col, fontsize=8)
        ax.set_ylabel("percentile")
        ax.tick_params(labelsize=7)
    axes[0].legend(fontsize=7)
    fig.suptitle("Feature percentile summary (p1/p25/p50/p75/p99 only -- no raw histogram)")
    fig.tight_layout()
    out = FIGURES_DIR / "feature_percentiles.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def categorical_value_counts(df: pd.DataFrame) -> dict:
    out = {}
    for col in CATEGORICAL_FEATURES:
        if col not in df.columns:
            continue
        out[col] = df[col].value_counts(dropna=False).to_dict()
    return out


def plot_categorical_value_counts(all_counts: dict[str, dict]) -> list[Path]:
    paths = []
    for col in CATEGORICAL_FEATURES:
        windows = [w for w in all_counts if col in all_counts[w]]
        if not windows:
            continue
        categories = sorted({k for w in windows for k in all_counts[w][col]}, key=str)
        fig, ax = plt.subplots(figsize=(7, 4))
        width = 0.35
        x = range(len(categories))
        for i, w in enumerate(windows):
            vals = [all_counts[w][col].get(c, 0) for c in categories]
            ax.bar([p + i * width for p in x], vals, width=width, label=w)
        ax.set_xticks([p + width / 2 for p in x])
        ax.set_xticklabels([str(c) for c in categories])
        ax.set_ylabel("loan count")
        ax.set_title(f"{col} (categorical rating code) value counts")
        ax.legend(fontsize=8)
        fig.tight_layout()
        out = FIGURES_DIR / f"{col.lower()}_value_counts.png"
        fig.savefig(out, dpi=130)
        plt.close(fig)
        paths.append(out)
    return paths


def plot_summary_table(all_rates: dict, all_flags: dict, all_refi: dict) -> Path:
    """Renders the plain-English side-by-side comparison table as an actual image."""
    windows = list(all_refi.keys())
    rows = [
        ["", *windows],
        ["FHA loans / refis / base rate", *[
            f"{all_refi[w]['fha']['n']:,} / {all_refi[w]['fha']['n_refi']:,} / "
            f"{all_refi[w]['fha']['base_rate']:.2%}" for w in windows
        ]],
        ["Conventional loans / refis / base rate", *[
            f"{all_refi[w]['conventional']['n']:,} / {all_refi[w]['conventional']['n_refi']:,} / "
            f"{all_refi[w]['conventional']['base_rate']:.2%}" for w in windows
        ]],
        ["Login_Count missing", *[f"{all_rates[w]['Login_Count']:.1f}%" for w in windows]],
        ["Census features missing", *[
            f"{all_rates[w]['Percent_HOUSING_TENURE_Occupied_housing_units_Owner_occupied']:.1f}%"
            for w in windows
        ]],
        ["SMOTE crash risk (F15)", *[
            ("No -- well under ceiling" if all(all_refi[w][u]["ratio"] < all_refi[w][u]["ceiling"]
             for u in UNIVERSE_BUCKETS) else "YES -- would crash") for w in windows
        ]],
        ["F5 bug (Flag_Trailing_DaysDiff_GT45 always 0)", *[
            ("Confirmed present" if all_flags[w]["Flag_Trailing_DaysDiff_GT45"]["pct_nonzero"] == 0
             else "Not present here") for w in windows
        ]],
    ]
    fig, ax = plt.subplots(figsize=(11, 0.42 * len(rows)))
    ax.axis("off")
    table = ax.table(cellText=rows, loc="upper center", cellLoc="left", bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.auto_set_column_width(col=list(range(len(rows[0]))))
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#444444")
        if r == 0:
            cell.set_text_props(weight="bold")
            cell.set_facecolor("#dddddd")
        else:
            cell.set_facecolor("#f7f7f7" if r % 2 == 0 else "white")
    ax.set_title("Exploratory Data Analysis", fontsize=12, weight="bold", pad=10)
    out = FIGURES_DIR / "summary_table.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    return out


def refi_rate_by_bucket(df: pd.DataFrame, value_col: str, bins: list, bin_labels: list) -> dict:
    """Refi rate per bucket, per universe. Aggregate only -- each bucket pools many loans."""
    out = {}
    cut = pd.cut(pd.to_numeric(df[value_col], errors="coerce"), bins=bins, labels=bin_labels)
    for universe, bucket in UNIVERSE_BUCKETS.items():
        sub = df[df["LoanType"].isin(bucket)].copy()
        sub["_bucket"] = cut.loc[sub.index]
        grouped = sub.groupby("_bucket", observed=True)["Refinanced_3_months_lookahead"].agg(["mean", "count"])
        out[universe] = {str(idx): (row["mean"], int(row["count"])) for idx, row in grouped.iterrows()}
    return out


def plot_refi_rate_by_bucket(data: dict, bin_labels: list, title: str, filename: str) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = {"fha": "tab:blue", "conventional": "tab:orange"}
    width = 0.35
    x = range(len(bin_labels))
    for i, (universe, buckets) in enumerate(data.items()):
        rates = [buckets.get(label, (0, 0))[0] * 100 for label in bin_labels]
        ax.bar([p + i * width for p in x], rates, width=width, label=universe, color=colors[universe])
    ax.set_xticks([p + width / 2 for p in x])
    ax.set_xticklabels(bin_labels, fontsize=8, rotation=20)
    ax.set_ylabel("refi rate %")
    ax.set_title(title)
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = FIGURES_DIR / filename
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def property_state_distribution(df: pd.DataFrame, top_n: int = 10) -> dict:
    """Top-N states by loan count -- aggregate counts over thousands of loans each."""
    return df["PropertyState"].value_counts().head(top_n).to_dict()


def plot_property_state_distribution(counts: dict, label: str) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    states = list(counts.keys())
    vals = list(counts.values())
    ax.bar(states, vals, color="tab:green")
    ax.set_ylabel("loan count")
    ax.set_title(f"Top {len(states)} states by loan count — {label}")
    fig.tight_layout()
    out = FIGURES_DIR / "property_state_distribution.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def loan_type_breakdown(df: pd.DataFrame) -> dict:
    return df["LoanType"].value_counts().to_dict()


def plot_loan_type_breakdown(all_breakdowns: dict[str, dict]) -> Path:
    windows = list(all_breakdowns.keys())
    types = sorted({t for w in windows for t in all_breakdowns[w]})
    fig, ax = plt.subplots(figsize=(7, 4.5))
    width = 0.35
    x = range(len(types))
    for i, w in enumerate(windows):
        vals = [all_breakdowns[w].get(t, 0) for t in types]
        ax.bar([p + i * width for p in x], vals, width=width, label=w)
    ax.set_xticks([p + width / 2 for p in x])
    ax.set_xticklabels(types)
    ax.set_ylabel("loan count")
    ax.set_title("LoanType sub-breakdown (FHA/VA, CONVENTIONAL/PMI)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = FIGURES_DIR / "loan_type_breakdown.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def payoff_data_refi_only_check() -> list[str]:
    path = DATA_REAL / "payoff_data" / "Combined_Payoff_Data_with_RefinanceYes.xlsx"
    df = pd.read_excel(path)
    lines = ["### Is payoff_data already refi-only? (F18/F25)", ""]
    for col in ("ReasonClosed", "Reason Closed_Redfin", "Refinance"):
        if col in df.columns:
            vc = df[col].value_counts(dropna=False)
            lines.append(f"- `{col}` value counts: {vc.to_dict()}")
        else:
            lines.append(f"- `{col}`: column not present")
    lines.append("")
    return lines


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Full EDA report (aggregate-only, auto-generated)", ""]

    lines.extend(payoff_data_refi_only_check())
    lines.extend(dtype_audit())

    all_null_rates, all_refi_rates, all_flags, all_percentiles, all_categoricals = {}, {}, {}, {}, {}

    for label, path in WINDOWS.items():
        if not path.exists():
            lines.append(f"### {label}: FILE NOT FOUND ({path})\n")
            continue
        df = pd.read_csv(path)

        rates = null_rates(df)
        all_null_rates[label] = rates
        lines.extend(null_rate_report(rates, label))

        flags = flag_variance(df)
        all_flags[label] = flags
        lines.extend(flag_variance_report(flags, label))

        refi = refi_rates(df)
        all_refi_rates[label] = refi
        lines.extend(refi_rate_report(refi, label))

        all_percentiles[label] = percentile_summary(df)
        all_categoricals[label] = categorical_value_counts(df)

    figure_paths = []
    if all_null_rates and all_flags and all_refi_rates:
        figure_paths.append(plot_summary_table(all_null_rates, all_flags, all_refi_rates))
    if all_null_rates:
        figure_paths.append(plot_null_rates(all_null_rates))
    if all_refi_rates:
        figure_paths.append(plot_loan_and_refi_counts(all_refi_rates))
        figure_paths.append(plot_refi_rates(all_refi_rates))
    if all_flags:
        figure_paths.append(plot_flag_variance(all_flags))
    if all_percentiles:
        figure_paths.append(plot_feature_percentiles(all_percentiles))
    if all_categoricals:
        figure_paths.extend(plot_categorical_value_counts(all_categoricals))

    # "More interesting" relationship EDA -- computed on the same-window data (the window
    # that matters for the eventual improved-model comparison). Aggregate rates/counts only,
    # each bucket/state/category pools hundreds-to-thousands of loans.
    same_window_path = WINDOWS.get("same_window_2026-02")
    if same_window_path and same_window_path.exists():
        df = pd.read_csv(same_window_path)

        fico_data = refi_rate_by_bucket(
            df, "FICO_Score", bins=[0, 619, 679, 739, 799, 900],
            bin_labels=["<620", "620-679", "680-739", "740-799", "800+"],
        )
        figure_paths.append(plot_refi_rate_by_bucket(
            fico_data, ["<620", "620-679", "680-739", "740-799", "800+"],
            "Refi rate by FICO bucket (same-window)", "refi_rate_by_fico.png",
        ))

        # pd.cut is right-closed by default: (-100,-2] groups -2.0 itself into the first
        # bucket, so the label is "<=-2" (not "<-2") to match -- same convention as the LTV
        # buckets below ("<=60" etc.), found during review.
        rate_delta_data = refi_rate_by_bucket(
            df, "Interest_Delta_Current_Market",
            bins=[-100, -2, -1, 0, 1, 100],
            bin_labels=["<=-2", "-2 to -1", "-1 to 0", "0 to 1", ">1"],
        )
        figure_paths.append(plot_refi_rate_by_bucket(
            rate_delta_data, ["<=-2", "-2 to -1", "-1 to 0", "0 to 1", ">1"],
            "Refi rate by note-vs-market rate delta (same-window)", "refi_rate_by_rate_delta.png",
        ))

        ltv_data = refi_rate_by_bucket(
            df, "CurrentLTV", bins=[0, 60, 80, 90, 95, 200],
            bin_labels=["<=60", "60-80", "80-90", "90-95", ">95"],
        )
        figure_paths.append(plot_refi_rate_by_bucket(
            ltv_data, ["<=60", "60-80", "80-90", "90-95", ">95"],
            "Refi rate by current LTV bucket (same-window)", "refi_rate_by_ltv.png",
        ))

        state_counts = property_state_distribution(df)
        figure_paths.append(plot_property_state_distribution(state_counts, "same-window"))

    all_loan_types = {label: loan_type_breakdown(pd.read_csv(p)) for label, p in WINDOWS.items() if p.exists()}
    if all_loan_types:
        figure_paths.append(plot_loan_type_breakdown(all_loan_types))
        for label, counts in all_loan_types.items():
            extra = {k: v for k, v in counts.items() if k not in ("FHA", "VA", "CONVENTIONAL", "PMI")}
            if extra:
                lines.append(
                    f"**Note ({label}):** `LoanType` values outside both universe buckets, "
                    f"silently excluded from training: {extra}"
                )
        lines.append("")

    lines.append("## Figures")
    lines.append("")
    for p in figure_paths:
        lines.append(f"- `{p.relative_to(ROOT)}`")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    for p in figure_paths:
        print(f"Wrote {p}")


if __name__ == "__main__":
    main()
