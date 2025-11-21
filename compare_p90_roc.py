"""
compare_p90_roc.py

Produces a single CSV that combines:
- Current flow data
- Rate of change (1h, 3h, 6h)
- Comparison to 90th percentile historical values

Output:
    data/high_flow_with_roc.csv
"""
# imports
import os
import pandas as pd
import numpy as np
from pathlib import Path

# directory and file paths
DATA_DIR = Path("data")
CURRENT_FILES = [
    DATA_DIR / "north_va.csv",
    DATA_DIR / "south_va.csv"
]
HISTORICAL_FILE = DATA_DIR / "historical_p90.csv"
OUTPUT_FILE = DATA_DIR / "high_flow_with_roc.csv"

WINDOWS = {"1h": 12, "3h": 36, "6h": 72}  # 5-minute data → 12 per hour

# roc functions
def compute_rate_of_change(df):
    df = df.copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
    df = df.sort_values(["site_no", "timestamp_utc"])

    # calculate percent change
    for label, window in WINDOWS.items():
        df[f"pct_change_{label}"] = (
            df.groupby("site_no")["flow_cfs"]
              .transform(lambda x: (x - x.shift(window)) / x.shift(window) * 100)
        )

    return df


# load current data
def load_current_data():
    dfs = []
    for file_path in CURRENT_FILES:
        if file_path.exists():
            region = "north" if "north" in file_path.name else "south"
            df = pd.read_csv(file_path)
            df["region"] = region
            dfs.append(df)
        else:
            print(f"Warning: missing {file_path}")
    # if no data found, return empty DataFrame
    if not dfs:
        print("No current data found. Exiting.")
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)

# prep current for comparison
def prepare_current_data(df):
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    df["day_of_year"] = df["timestamp_utc"].dt.dayofyear
    return df.dropna(subset=["day_of_year", "flow_cfs", "site_no"])

# compare current to P90
def compare_to_historical(df_current, df_hist):
    merged = pd.merge(
        df_current,
        df_hist,
        how="left",
        on=["site_no", "day_of_year"],
        suffixes=("_current", "_hist")
    )

    # fix site names
    if "site_name_current" in merged.columns:
        merged["site_name"] = merged["site_name_current"]
    elif "site_name_hist" in merged.columns:
        merged["site_name"] = merged["site_name_hist"]
    else:
        merged["site_name"] = "unknown"

    # check p90 exists
    if "p90_flow_cfs" not in merged.columns:
        merged["p90_flow_cfs"] = np.nan

    # ratio calculations
    merged["ratio"] = merged["flow_cfs"] / merged["p90_flow_cfs"]
    merged.loc[merged["p90_flow_cfs"].isna() | (merged["p90_flow_cfs"] == 0), "ratio"] = np.nan
    merged["high_flow"] = merged["ratio"] >= 1.0

    # outpot columns — include ROC if present
    columns = [
        "site_no", "site_name", "timestamp_utc", "region",
        "lat", "lon",
        "flow_cfs", "p90_flow_cfs",
        "ratio", "high_flow",
        "pct_change_1h", "pct_change_3h", "pct_change_6h"
    ]

    existing = [c for c in columns if c in merged.columns]
    return merged[existing]

# main
def main():
    print("Loading current data...")
    df_current = load_current_data()
    if df_current.empty:
        return

    print("Computing rate of change...")
    df_current = compute_rate_of_change(df_current)

    print("Preparing current data...")
    df_current = prepare_current_data(df_current)

    if not HISTORICAL_FILE.exists():
        print("Historical file missing! Run fetch_historical_data.py first.")
        return

    print("Loading historical percentiles...")
    df_hist = pd.read_csv(HISTORICAL_FILE)

    print("Joining with historical p90 data...")
    df_out = compare_to_historical(df_current, df_hist)

    print(f"Saving → {OUTPUT_FILE}")
    df_out.to_csv(OUTPUT_FILE, index=False)

    # Summary
    high_flow_sites = df_out[df_out["high_flow"]].groupby("site_no")["site_name"].first()
    if len(high_flow_sites) > 0:
        print("\nHigh flow sites:")
        for site_no, site_name in high_flow_sites.items():
            print(f"  • {site_no}: {site_name}")
    else:
        print("\nNo sites above 90th percentile.")

    print("Done!")

# entry
if __name__ == "__main__":
    main()