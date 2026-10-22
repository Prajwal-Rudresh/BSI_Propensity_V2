"""Trim data/real/ files to the exact date windows this backtest needs.

Writes new, smaller files alongside the originals (originals are left in place).
Only ever touches dates for filtering — no row-level content is printed or
returned, consistent with the aggregate-only handling used throughout this
backtest folder.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA_REAL = HERE.parent / "data" / "real"
REPORT_PATH = HERE.parent / "reports" / "trim_report.md"

ONE_OFF_SRC = DATA_REAL / "one_off" / "one_off_oct23_to_Feb25.csv"
ONE_OFF_DST = DATA_REAL / "one_off" / "one_off_trimmed_2025-07_2026-06.csv"
ONE_OFF_START, ONE_OFF_END = "2025-07-01", "2026-06-30"

MLW_SRC = DATA_REAL / "mlw_logins" / "MLW_logins.csv"
MLW_DST = DATA_REAL / "mlw_logins" / "mlw_logins_trimmed_2025-12_2026-06.csv"
MLW_START, MLW_END = "2025-12-01", "2026-06-30"


def trim_csv(src: Path, dst: Path, date_col: str, start: str, end: str) -> tuple[int, int]:
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    kept_total = 0
    read_total = 0
    first = True
    for chunk in pd.read_csv(src, chunksize=200_000, low_memory=False):
        read_total += len(chunk)
        parsed = pd.to_datetime(chunk[date_col], errors="coerce")
        mask = (parsed >= start_ts) & (parsed <= end_ts)
        kept = chunk.loc[mask]
        kept_total += len(kept)
        kept.to_csv(dst, mode="w" if first else "a", header=first, index=False)
        first = False
    return read_total, kept_total


def main() -> None:
    lines = ["# Trim report (aggregate-only, auto-generated)", ""]

    for label, src, dst, col, start, end in [
        ("one_off", ONE_OFF_SRC, ONE_OFF_DST, "DataDate", ONE_OFF_START, ONE_OFF_END),
        ("mlw_logins", MLW_SRC, MLW_DST, "Date", MLW_START, MLW_END),
    ]:
        if not src.exists():
            lines.append(f"## {label}: SOURCE NOT FOUND ({src})")
            continue
        read_n, kept_n = trim_csv(src, dst, col, start, end)
        lines.append(f"## {label}")
        lines.append(f"- source: `{src.name}` ({read_n} rows)")
        lines.append(f"- window: `{col}` in [{start}, {end}]")
        lines.append(f"- trimmed file: `{dst.name}` ({kept_n} rows kept, "
                      f"{read_n - kept_n} dropped)")
        lines.append("")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    sys.exit(main())
