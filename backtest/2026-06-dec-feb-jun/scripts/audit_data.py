"""Aggregate-only audit of backtest/2026-06-dec-feb-jun/data/real/.

Reads each real input file and writes ONLY aggregate facts (row count, column
names, date-range of any date-like column) to reports/data_audit.md. Never
prints or returns row-level content. Run this, don't eyeball the source files.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BACKTEST_ROOT = HERE.parent
DATA_REAL = BACKTEST_ROOT / "data" / "real"
REPORT_DIR = BACKTEST_ROOT / "reports"
REPORT_PATH = REPORT_DIR / "data_audit.md"

# Files that are just folder placeholders / already-authored docs, not data.
SKIP_NAMES = {".gitkeep", "README.md", "MANIFEST.md"}

DATE_NAME_HINTS = (
    "date", "month", "year_month", "yearmonth", "obs", "snapshot", "period",
)


def find_data_files() -> list[Path]:
    files: list[Path] = []
    for sub in sorted(DATA_REAL.iterdir()):
        if not sub.is_dir():
            continue
        for f in sorted(sub.iterdir()):
            if f.name in SKIP_NAMES or f.name.startswith("."):
                continue
            if f.is_file():
                files.append(f)
    return files


def read_columns_and_count(path: Path) -> tuple[list[str], int]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        head = pd.read_csv(path, nrows=0)
        columns = list(head.columns)
        row_count = 0
        for chunk in pd.read_csv(path, usecols=[columns[0]], chunksize=200_000):
            row_count += len(chunk)
        return columns, row_count
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path)
        return list(df.columns), len(df)
    else:
        return [], -1


def candidate_date_columns(columns: list[str]) -> list[str]:
    return [c for c in columns if any(h in c.lower() for h in DATE_NAME_HINTS)]


def date_min_max_csv(path: Path, col: str) -> tuple[str, str] | None:
    lo = None
    hi = None
    try:
        for chunk in pd.read_csv(path, usecols=[col], chunksize=200_000):
            parsed = pd.to_datetime(chunk[col], errors="coerce")
            parsed = parsed.dropna()
            if parsed.empty:
                continue
            cur_lo, cur_hi = parsed.min(), parsed.max()
            lo = cur_lo if lo is None or cur_lo < lo else lo
            hi = cur_hi if hi is None or cur_hi > hi else hi
    except Exception as e:  # noqa: BLE001
        return None
    if lo is None:
        return None
    return str(lo.date()), str(hi.date())


def date_min_max_excel(df: pd.DataFrame, col: str) -> tuple[str, str] | None:
    parsed = pd.to_datetime(df[col], errors="coerce").dropna()
    if parsed.empty:
        return None
    return str(parsed.min().date()), str(parsed.max().date())


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Data audit (aggregate-only, auto-generated)", ""]
    files = find_data_files()
    if not files:
        lines.append("No data files found under data/real/.")
    for path in files:
        rel = path.relative_to(DATA_REAL)
        lines.append(f"## {rel}")
        suffix = path.suffix.lower()
        try:
            if suffix == ".csv":
                head = pd.read_csv(path, nrows=0)
                columns = list(head.columns)
                row_count = 0
                for chunk in pd.read_csv(path, usecols=[columns[0]], chunksize=200_000):
                    row_count += len(chunk)
                lines.append(f"- rows: {row_count}")
                lines.append(f"- columns ({len(columns)}): {columns}")
                for col in candidate_date_columns(columns):
                    mm = date_min_max_csv(path, col)
                    if mm:
                        lines.append(f"- `{col}` range: {mm[0]} to {mm[1]}")
                    else:
                        lines.append(f"- `{col}` range: could not parse as dates")
            elif suffix in (".xlsx", ".xls"):
                df = pd.read_excel(path)
                columns = list(df.columns)
                lines.append(f"- rows: {len(df)}")
                lines.append(f"- columns ({len(columns)}): {columns}")
                for col in candidate_date_columns(columns):
                    mm = date_min_max_excel(df, col)
                    if mm:
                        lines.append(f"- `{col}` range: {mm[0]} to {mm[1]}")
                    else:
                        lines.append(f"- `{col}` range: could not parse as dates")
            else:
                lines.append(f"- (unrecognized extension {suffix!r}, skipped)")
        except Exception as e:  # noqa: BLE001
            lines.append(f"- ERROR reading file: {type(e).__name__}: {e}")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    sys.exit(main())
