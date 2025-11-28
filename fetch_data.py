"""
fetch_data.py - Incremental real-time VA discharge fetch

Fetches only readings since the last timestamp.
Keeps a rolling 24-hour window.
Handles empty fetches safely.
Includes latitude and longitude columns.
Saves all data into a single CSV.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import numpy as np 

# ------------------------------
# CONFIG
# ------------------------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, "gauge_data.csv")

NWIS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"

# ------------------------------
# HELPER FUNCTIONS
# ------------------------------

def fetch_va_iv_since(start_time):
    """
    Fetch all VA gauges discharge readings since start_time
    """
    end_time = datetime.now(timezone.utc)

    params = {
        "format": "json",
        "stateCd": "VA",
        "parameterCd": "00060",
        "siteType": "ST",
        "siteStatus": "active",
        "startDT": start_time.strftime("%Y-%m-%dT%H:%M"),
        "endDT": end_time.strftime("%Y-%m-%dT%H:%M")
    }

    resp = requests.get(NWIS_IV_URL, params=params, timeout=30)
    resp.raise_for_status()
    j = resp.json()

    rows = []
    for ts in j.get("value", {}).get("timeSeries", []):
        site_no = ts["sourceInfo"]["siteCode"][0]["value"]
        site_name = ts["sourceInfo"]["siteName"]
        lat = ts["sourceInfo"]["geoLocation"]["geogLocation"]["latitude"]
        lon = ts["sourceInfo"]["geoLocation"]["geogLocation"]["longitude"]
        for v in ts["values"][0]["value"]:
            try:
                flow = float(v["value"])
                if flow == -9999:   # convert USGS missing value code to NaN
                    flow = np.nan
            except (TypeError, ValueError):
                flow = np.nan
            timestamp = v["dateTime"]
            rows.append({
                "site_no": site_no,
                "site_name": site_name,
                "timestamp_utc": timestamp,
                "flow_cfs": flow,
                "latitude": lat,
                "longitude": lon
            })
    df = pd.DataFrame(rows)
    return df

def load_last_timestamp(file_path):
    """
    Get the last timestamp from an existing CSV or return 24h ago if file missing
    """
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
        last_time = df["timestamp_utc"].max()
        # Add 1 second to avoid duplicate
        return last_time + timedelta(seconds=1)
    else:
        return datetime.now(timezone.utc) - timedelta(hours=24)

def append_and_trim(df_new, file_path, hours=24):
    """
    Append new data to CSV and keep only last X hours
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    if os.path.exists(file_path):
        df_old = pd.read_csv(file_path)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new.copy()

    df_all["timestamp_utc"] = pd.to_datetime(df_all["timestamp_utc"], format="ISO8601", utc=True)
    df_all = df_all[df_all["timestamp_utc"] >= cutoff_time]
    df_all.to_csv(file_path, index=False)
    print(f"Saved {len(df_all)} rows to {file_path}")

# ------------------------------
# MAIN
# ------------------------------

def main():
    # Determine last timestamp
    last_time = load_last_timestamp(DATA_FILE)

    # Fetch new readings since last timestamp
    df = fetch_va_iv_since(last_time)
    print(f"Fetched {len(df)} readings total.")

    if not df.empty:
        append_and_trim(df, DATA_FILE)
        print("Update complete!")
    else:
        print("No new readings since last timestamp. Nothing to update.")

# ------------------------------
# ENTRY POINT
# ------------------------------
if __name__ == "__main__":
    main()
