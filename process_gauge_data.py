import os
import pandas as pd
import numpy as np
from pathlib import Path

# directory and file paths
DATA_DIR = Path("data")
GAUGE_FILE = DATA_DIR / "gauge_data.csv"
HISTORICAL_FILE = DATA_DIR / "historical_p90.csv"
OUTPUT_FILE = DATA_DIR / "gauge_data_processed.csv"

WINDOWS = {"1h": 12, "3h": 36, "6h": 72}

# calculate rate of change
def compute_rate_of_change(df):
    df = df.copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df = df.sort_values(["site_no", "timestamp_utc"])

    for label, window in WINDOWS.items():
        df[f"pct_change_{label}"] = (
            df.groupby("site_no")["flow_cfs"]
              .transform(lambda x: (x - x.shift(window)) / x.shift(window) * 100)
        )

    return df

# prepare current data for comparison
def prepare_current_data(df):
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    df["day_of_year"] = df["timestamp_utc"].dt.dayofyear
    return df.dropna(subset=["day_of_year", "flow_cfs", "site_no"])


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
    print(f"Saved processed dataset → {OUTPUT_FILE}")

# entry
if __name__ == "__main__":
    main()
