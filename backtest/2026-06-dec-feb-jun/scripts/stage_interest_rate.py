"""Stage the real interest-rate file at the two paths/formats the legacy code hardcodes.

Pure format staging: same content, no values touched, no rows printed. The
training script expects a CSV named Curinos_Interest_Rate_File_2022-2024.csv;
the scoring script already expects an xlsx named 'Interest Rate Data.xlsx'.
"""
import shutil
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BACKTEST_ROOT = HERE.parent
SRC = BACKTEST_ROOT / "data" / "real" / "interest_rate" / "Interest Rate Data.xlsx"

TRAIN_DST = BACKTEST_ROOT / "data_preperation" / "Input" / "Curinos_Interest_Rate_File_2022-2024.csv"
SCORE_DST = BACKTEST_ROOT / "inference_data" / "Interest Rate Data.xlsx"

df = pd.read_excel(SRC)
TRAIN_DST.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(TRAIN_DST, index=False)
SCORE_DST.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(SRC, SCORE_DST)
print(f"Wrote {TRAIN_DST} ({len(df)} rows) and copied to {SCORE_DST}")
