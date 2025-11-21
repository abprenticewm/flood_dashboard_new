import pandas as pd
from pathlib import Path

WINDOWS = {"1h": 12, "3h": 36, "6h": 72}  # 5-min intervals → 12 per hour

def compute_rate_of_change(df):
    df = df.copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
    df = df.sort_values(["site_no", "timestamp_utc"])

    # Calculate percent change using transform for index alignment
    for label, window in WINDOWS.items():
        df[f"pct_change_{label}"] = (
            df.groupby("site_no")["flow_cfs"]
              .transform(lambda x: (x - x.shift(window)) / x.shift(window) * 100)
        )

    # Keep only the most recent record for each site
    latest = (
        df.sort_values("timestamp_utc")
          .groupby("site_no", as_index=False)
          .tail(1)
          .reset_index(drop=True)
    )

    # Select relevant columns
    keep_cols = [
        "site_no", "site_name", "timestamp_utc", "flow_cfs",
        "pct_change_1h", "pct_change_3h", "pct_change_6h"
    ]
    latest = latest[[c for c in keep_cols if c in latest.columns]]

    return latest


def main():
    print("Analyzing streamflow rate of change...")

    data_dir = Path("data")
    output_dir = Path("data/derived")
    output_dir.mkdir(exist_ok=True, parents=True)

    for region in ["north_va", "south_va"]:
        file_path = data_dir / f"{region}.csv"
        if not file_path.exists():
            print(f"⚠️ File not found: {file_path}")
            continue

        df = pd.read_csv(file_path)
        if df.empty:
            print(f"⚠️ {region}.csv is empty — skipping.")
            continue

        result = compute_rate_of_change(df)
        output_path = output_dir / f"{region}_rate_of_change.csv"
        result.to_csv(output_path, index=False)
        print(f"✅ Saved rate of change results to {output_path}")

    print("Done!")


if __name__ == "__main__":
    main()
