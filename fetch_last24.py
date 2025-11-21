"""
fetch_last24.py - Fetch last 24 hours of VA discharge data for testing

Fetches USGS IV data for all VA gauges for the past 24 hours.
Splits into North/South CSVs for testing.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# directory and file paths
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

NORTH_FILE = os.path.join(DATA_DIR, "north_va_last24.csv")
SOUTH_FILE = os.path.join(DATA_DIR, "south_va_last24.csv")

NWIS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"
LATITUDE_MIDPOINT = 37.5  # VA split north/south

# helpers
def fetch_va_iv_last24():
    """
    Fetch all VA gauges discharge readings for the last 24 hours.
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=24)
    # build request parameters
    params = {
        "format": "json",
        "stateCd": "VA",
        "parameterCd": "00060",
        "siteType": "ST",
        "siteStatus": "active",
        "startDT": start_time.strftime("%Y-%m-%dT%H:%M"),
        "endDT": end_time.strftime("%Y-%m-%dT%H:%M")
    }
    # fetch data
    print("Fetching last 24 hours of data from USGS IV...")
    resp = requests.get(NWIS_IV_URL, params=params, timeout=30)
    resp.raise_for_status()
    j = resp.json()

    rows = []
    for ts in j.get("value", {}).get("timeSeries", []):
        site_no = ts["sourceInfo"]["siteCode"][0]["value"]
        site_name = ts["sourceInfo"]["siteName"]
        lat = ts["sourceInfo"]["geoLocation"]["geogLocation"]["latitude"]
        for v in ts["values"][0]["value"]:
            try:
                flow = float(v["value"])
            except (TypeError, ValueError):
                flow = None
            timestamp = v["dateTime"]
            rows.append({
                "site_no": site_no,
                "site_name": site_name,
                "timestamp_utc": timestamp,
                "flow_cfs": flow,
                "north_south": "north" if lat >= LATITUDE_MIDPOINT else "south"
            })
    df = pd.DataFrame(rows)
    return df

def save_north_south(df):
    """
    Save north/south data to separate CSVs
    """
    if df.empty:
        print("No data fetched for the last 24 hours.")
        return

    north_df = df[df["north_south"] == "north"].drop(columns=["north_south"])
    south_df = df[df["north_south"] == "south"].drop(columns=["north_south"])
    north_df.to_csv(NORTH_FILE, index=False)
    south_df.to_csv(SOUTH_FILE, index=False)
    print(f"Saved {len(north_df)} rows to {NORTH_FILE}")
    print(f"Saved {len(south_df)} rows to {SOUTH_FILE}")

# main
def main():
    df = fetch_va_iv_last24()
    print(f"Fetched {len(df)} readings total.")
    save_north_south(df)

if __name__ == "__main__":
    main()
