"""
compare_current_to_p90.py - Identify high-flow days compared to 20-year baseline

Compares current Virginia streamflow data to the 90th percentile
historical values for each site/day-of-year.

Output:
    data/high_flow_summary.csv
"""

import os
import pandas as pd
from datetime import datetime
import numpy as np

# ------------------------------
# CONFIG
# ------------------------------
DATA_DIR = "data"
CURRENT_FILES = [
    os.path.join(DATA_DIR, "north_va.csv"),
    os.path.join(DATA_DIR, "south_va.csv")
]
HISTORICAL_FILE = os.path.join(DATA_DIR, "historical_p90.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "high_flow_summary.csv")

# ------------------------------
# HELPER FUNCTIONS
# ------------------------------

def load_current_data():
    """Load recent flow data from north and south CSVs."""
    dfs = []
    for file_path in CURRENT_FILES:
        if os.path.exists(file_path):
            region = "north" if "north" in file_path else "south"
            df = pd.read_csv(file_path)
            df["region"] = region
            dfs.append(df)
        else:
            print(f"Warning: {file_path} not found — skipping.")
    if not dfs:
        print("No current data found. Exiting.")
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def prepare_current_data(df):
    """Add day-of-year column for joining with historical percentiles."""
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    df["day_of_year"] = df["timestamp_utc"].dt.dayofyear
    return df.dropna(subset=["day_of_year", "flow_cfs", "site_no"])


def compare_to_historical(df_current, df_hist):
    """Merge and compare current flow readings to 90th percentile values."""
    merged = pd.merge(
        df_current,
        df_hist,
        how="left",
        left_on=["site_no", "day_of_year"],
        right_on=["site_no", "day_of_year"],
        suffixes=("_current", "_hist")
    )

    # Choose site_name from available columns
    if "site_name_current" in merged.columns:
        merged["site_name"] = merged["site_name_current"]
    elif "site_name_hist" in merged.columns:
        merged["site_name"] = merged["site_name_hist"]
    elif "site_name" not in merged.columns:
        merged["site_name"] = "unknown"

    # Ensure p90_flow_cfs exists (may be NaN)
    if "p90_flow_cfs" not in merged.columns:
        merged["p90_flow_cfs"] = np.nan

    # Safe ratio: avoid division by zero / NaN
    merged["ratio"] = merged["flow_cfs"] / merged["p90_flow_cfs"]
    merged.loc[merged["p90_flow_cfs"].isna() | (merged["p90_flow_cfs"] == 0), "ratio"] = np.nan

    merged["high_flow"] = merged["ratio"] >= 1.0

    # Build output columns; include lat/lon and any pct_change fields present
    cols = [
        "site_no",
        "site_name",
        "timestamp_utc",
        "flow_cfs",
        "p90_flow_cfs",
        "ratio",
        "high_flow",
        "region",
        "lat",
        "lon",
    ]

    # include rate-of-change columns if present
    for c in ["pct_change_1h", "pct_change_3h", "pct_change_6h"]:
        if c in merged.columns:
            cols.append(c)

    existing_cols = [c for c in cols if c in merged.columns]
    return merged[existing_cols]


# ------------------------------
# MAIN
# ------------------------------

def main():
    print("Comparing current data to historical 90th percentile thresholds...")

    # Load current and historical data
    df_current = load_current_data()
    if df_current.empty:
        return

    if not os.path.exists(HISTORICAL_FILE):
        print("Historical file not found! Run fetch_historical_data.py first.")
        return

    df_hist = pd.read_csv(HISTORICAL_FILE)
    if df_hist.empty:
        print("Historical dataset is empty. Run fetch_historical_data.py again.")
        return

    # Prep and compare
    df_current = prepare_current_data(df_current)
    df_results = compare_to_historical(df_current, df_hist)

    # Save results
    df_results.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved comparison results → {OUTPUT_FILE}")

    # Summary
    if "high_flow" in df_results.columns:
        high_flow_sites = (
            df_results[df_results["high_flow"]]
            .groupby("site_no")["site_name"]
            .first()
        )
        if len(high_flow_sites) > 0:
            print("\nHigh flow sites detected:")
            for site_no, site_name in high_flow_sites.items():
                print(f"  - {site_no}: {site_name}")
        else:
            print("\nNo sites above 90th percentile today.")
    else:
        print("No high_flow column detected — check historical data formatting.")


# ------------------------------
# ENTRY POINT
# ------------------------------
if __name__ == "__main__":
    main()


# """
# compare_current_to_p90.py - Identify high-flow days compared to 20-year baseline

# Compares current Virginia streamflow data to the 90th percentile
# historical values for each site/day-of-year.

# Output:
#     data/high_flow_summary.csv
# """

# import os
# import pandas as pd
# from datetime import datetime

# # ------------------------------
# # CONFIG
# # ------------------------------
# DATA_DIR = "data"
# CURRENT_FILES = [
#     os.path.join(DATA_DIR, "north_va.csv"),
#     os.path.join(DATA_DIR, "south_va.csv")
# ]
# HISTORICAL_FILE = os.path.join(DATA_DIR, "historical_p90.csv")
# OUTPUT_FILE = os.path.join(DATA_DIR, "high_flow_summary.csv")

# # ------------------------------
# # HELPER FUNCTIONS
# # ------------------------------

# def load_current_data():
#     """Load recent flow data from north and south CSVs."""
#     dfs = []
#     for file_path in CURRENT_FILES:
#         if os.path.exists(file_path):
#             region = "north" if "north" in file_path else "south"
#             df = pd.read_csv(file_path)
#             df["region"] = region
#             dfs.append(df)
#         else:
#             print(f"Warning: {file_path} not found — skipping.")
#     if not dfs:
#         print("No current data found. Exiting.")
#         return pd.DataFrame()
#     return pd.concat(dfs, ignore_index=True)


# def prepare_current_data(df):
#     """Add day-of-year column for joining with historical percentiles."""
#     df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
#     df["day_of_year"] = df["timestamp_utc"].dt.dayofyear
#     return df.dropna(subset=["day_of_year", "flow_cfs", "site_no"])


# def compare_to_historical(df_current, df_hist):
#     """Merge and compare current flow readings to 90th percentile values."""
#     merged = pd.merge(
#         df_current,
#         df_hist,
#         how="left",
#         left_on=["site_no", "day_of_year"],
#         right_on=["site_no", "day_of_year"],
#         suffixes=("_current", "_hist")
#     )

#     # Handle possible duplicate or missing site_name columns
#     if "site_name_current" in merged.columns:
#         merged["site_name"] = merged["site_name_current"]
#     elif "site_name_hist" in merged.columns:
#         merged["site_name"] = merged["site_name_hist"]
#     elif "site_name" not in merged.columns:
#         merged["site_name"] = "unknown"

#     # Calculate ratio and flag
#     merged["ratio"] = merged["flow_cfs"] / merged["p90_flow_cfs"]
#     merged["high_flow"] = merged["ratio"] >= 1.0

#     # Select output columns safely
#     cols = [
#         "site_no",
#         "site_name",
#         "timestamp_utc",
#         "flow_cfs",
#         "p90_flow_cfs",
#         "ratio",
#         "high_flow",
#         "region"
#     ]
#     existing_cols = [c for c in cols if c in merged.columns]
#     return merged[existing_cols]


# # ------------------------------
# # MAIN
# # ------------------------------

# def main():
#     print("Comparing current data to historical 90th percentile thresholds...")

#     # Load current and historical data
#     df_current = load_current_data()
#     if df_current.empty:
#         return

#     if not os.path.exists(HISTORICAL_FILE):
#         print("Historical file not found! Run fetch_historical_data.py first.")
#         return

#     df_hist = pd.read_csv(HISTORICAL_FILE)
#     if df_hist.empty:
#         print("Historical dataset is empty. Run fetch_historical_data.py again.")
#         return

#     # Prep and compare
#     df_current = prepare_current_data(df_current)
#     df_results = compare_to_historical(df_current, df_hist)

#     # Save results
#     df_results.to_csv(OUTPUT_FILE, index=False)
#     print(f"Saved comparison results → {OUTPUT_FILE}")

#     # Summary
#     if "high_flow" in df_results.columns:
#         high_flow_sites = (
#             df_results[df_results["high_flow"]]
#             .groupby("site_no")["site_name"]
#             .first()
#         )
#         if len(high_flow_sites) > 0:
#             print("\nHigh flow sites detected:")
#             for site_no, site_name in high_flow_sites.items():
#                 print(f"  - {site_no}: {site_name}")
#         else:
#             print("\nNo sites above 90th percentile today.")
#     else:
#         print("No high_flow column detected — check historical data formatting.")


# # ------------------------------
# # ENTRY POINT
# # ------------------------------
# if __name__ == "__main__":
#     main()