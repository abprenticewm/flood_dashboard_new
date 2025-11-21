<<<<<<< HEAD
import os
import pandas as pd
import numpy as np
from pathlib import Path

# directory and file paths
=======
"""
process_gauge_data.py

1. Reads gauge_data.csv from data/ (output of fetch_data.py)
2. Computes 1h, 3h, 6h percent change for each site
3. Compares latest readings to historical 90th percentile (P90)
4. Outputs a single CSV with one row per gauge
"""

import os
import pandas as pd
from pathlib import Path
from datetime import datetime

# ------------------------------
# CONFIG
# ------------------------------
>>>>>>> 9cd881de4f1e7dff2374064056774b5d98147652
DATA_DIR = Path("data")
GAUGE_FILE = DATA_DIR / "gauge_data.csv"
HISTORICAL_FILE = DATA_DIR / "historical_p90.csv"
OUTPUT_FILE = DATA_DIR / "gauge_data_processed.csv"

<<<<<<< HEAD
WINDOWS = {"1h": 12, "3h": 36, "6h": 72}

# calculate rate of change
=======
WINDOWS = {"1h": 12, "3h": 36, "6h": 72}  # 5-min intervals → 12 per hour

# ------------------------------
# HELPER FUNCTIONS
# ------------------------------

>>>>>>> 9cd881de4f1e7dff2374064056774b5d98147652
def compute_rate_of_change(df):
    df = df.copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df = df.sort_values(["site_no", "timestamp_utc"])

<<<<<<< HEAD
=======
    # Calculate percent change for each window
>>>>>>> 9cd881de4f1e7dff2374064056774b5d98147652
    for label, window in WINDOWS.items():
        df[f"pct_change_{label}"] = (
            df.groupby("site_no")["flow_cfs"]
              .transform(lambda x: (x - x.shift(window)) / x.shift(window) * 100)
        )

    return df

<<<<<<< HEAD
# prepare current data for comparison
def prepare_current_data(df):
=======
def prepare_current_data(df):
    """Add day-of-year column for historical comparison"""
>>>>>>> 9cd881de4f1e7dff2374064056774b5d98147652
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    df["day_of_year"] = df["timestamp_utc"].dt.dayofyear
    return df.dropna(subset=["day_of_year", "flow_cfs", "site_no"])

<<<<<<< HEAD

# merge with historical P90 data and compute ratios
def compare_to_historical(df_cur, df_hist):
    merged = pd.merge(
        df_cur,
        df_hist,
        on=["site_no", "day_of_year"],
        how="left",
        suffixes=("", "_hist")
    )

    # if historical provided a site_name, prefer current name
    if "site_name_hist" in merged.columns and "site_name" not in merged.columns:
        merged["site_name"] = merged["site_name_hist"]

    # clean p90_flow_cfs
    merged["p90_flow_cfs"] = pd.to_numeric(merged["p90_flow_cfs"], errors="coerce")

    # remove invalid or zero values (no divide zero)
    merged.loc[(merged["p90_flow_cfs"] <= 0) | (merged["p90_flow_cfs"].isna()), "p90_flow_cfs"] = np.nan

    # compute ratio (flow / P90)
    merged["ratio"] = merged["flow_cfs"] / merged["p90_flow_cfs"]

    # if P90 is missing → ratio is NA
    merged.loc[merged["p90_flow_cfs"].isna(), "ratio"] = np.nan

    # high flow indicator
    merged["high_flow"] = merged["ratio"] >= 1.0

    # convert ratio percentile
    merged["percentile"] = merged["ratio"] * 100

    # remove invalid values
    merged["percentile"] = merged["percentile"].replace([np.inf, -np.inf], np.nan)
    merged["percentile"] = pd.to_numeric(merged["percentile"], errors="coerce")

    # restrict to valid range
    merged.loc[merged["percentile"] < 0, "percentile"] = 0
    merged.loc[merged["percentile"] > 500, "percentile"] = 500  # cap extreme spikes
    merged["percentile"] = merged["percentile"].fillna(0)

    return merged

# main
def main():
    if not GAUGE_FILE.exists() or not HISTORICAL_FILE.exists():
        print("Missing input files! Run fetch_data AND fetch_historical first.")
        return

    df = pd.read_csv(GAUGE_FILE, dtype={"site_no": str})
    df_hist = pd.read_csv(HISTORICAL_FILE, dtype={"site_no": str})

    df = compute_rate_of_change(df)
    df = prepare_current_data(df)
    df = compare_to_historical(df, df_hist)

    # keep one row per site (most recent)
    df_latest = (
        df.sort_values("timestamp_utc")
          .drop_duplicates("site_no", keep="last")
    )

    # ensure final column names
    if "site_name_x" in df_latest.columns:
        df_latest.rename(columns={"site_name_x": "site_name"}, inplace=True)
    if "site_name_y" in df_latest.columns:
        df_latest.rename(columns={"site_name_y": "site_name"}, inplace=True)

    df_latest.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Saved processed dataset → {OUTPUT_FILE}")

# entry
if __name__ == "__main__":
    main()
=======
def compare_to_historical(df_current, df_hist):
    """Merge with historical P90 flows and compute percentile ratio"""
    merged = pd.merge(
        df_current,
        df_hist,
        how="left",
        left_on=["site_no", "day_of_year"],
        right_on=["site_no", "day_of_year"],
        suffixes=("", "_hist")
    )

    # Use site_name from current or fallback to historical
    if "site_name" not in merged.columns and "site_name_hist" in merged.columns:
        merged["site_name"] = merged["site_name_hist"]

    # Compute percentile ratio
    merged["percentile"] = merged["flow_cfs"] / merged["p90_flow_cfs"]

    return merged

# ------------------------------
# MAIN
# ------------------------------

def main():
    print("Processing gauge data...")

    # Load current gauge data
    if not GAUGE_FILE.exists():
        print(f"Gauge data not found at {GAUGE_FILE}. Run fetch_data.py first.")
        return

    df_current = pd.read_csv(GAUGE_FILE)
    if df_current.empty:
        print("Gauge data is empty. Exiting.")
        return

    # Compute percent changes
    df_current = compute_rate_of_change(df_current)

    # Prepare for historical comparison
    df_current = prepare_current_data(df_current)

    # Merge with historical P90 if available
    if HISTORICAL_FILE.exists():
        df_hist = pd.read_csv(HISTORICAL_FILE)
        df_final = compare_to_historical(df_current, df_hist)
    else:
        print(f"Historical P90 file not found at {HISTORICAL_FILE}. Skipping percentile calculation.")
        df_final = df_current.copy()
        df_final["percentile"] = pd.NA

    # Keep only the most recent record per gauge
    df_final["timestamp_utc"] = pd.to_datetime(df_final["timestamp_utc"], utc=True)
    df_final = (
        df_final.sort_values("timestamp_utc")
                .groupby("site_no", as_index=False)
                .tail(1)
    )

    # Select final columns
    columns = [
        "site_no",
        "site_name",
        "timestamp_utc",
        "flow_cfs",
        "pct_change_1h",
        "pct_change_3h",
        "pct_change_6h",
        "percentile",
        "longitude",
        "latitude"
    ]
    df_final = df_final[[c for c in columns if c in df_final.columns]]

    # Save final CSV
    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Saved processed gauge data to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
>>>>>>> 9cd881de4f1e7dff2374064056774b5d98147652
