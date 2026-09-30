from pathlib import Path
import pandas as pd

RAW = Path("data/raw")

for f in sorted(RAW.glob("*.csv")):
    df = pd.read_csv(f)
    print("=" * 70)
    print(f"{f.name}  |  rows: {len(df):,}  |  "
          f"memory: {df.memory_usage(deep=True).sum()/1e6:.1f} MB")
    print("columns:", list(df.columns))
    print(df.dtypes.to_string())
    print(df.head(3).to_string())