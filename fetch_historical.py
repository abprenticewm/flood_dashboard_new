"""
fetch_historical_data.py - Build 20-year Virginia streamflow reference dataset

Downloads daily discharge data (00060) for all Virginia stream gauges
from USGS NWIS Daily Values service. Computes 90th percentile flow for
each day of year across 20 years per site.

Output:
    data/historical_p90.csv
    Columns: site_no, site_name, day_of_year, p90_flow_cfs, north_south
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

# directory and file paths
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

HISTORICAL_FILE = os.path.join(DATA_DIR, "historical_p90.csv")
NWIS_DV_URL = "https://waterservices.usgs.gov/nwis/dv/"
LATITUDE_MIDPOINT = 37.5  # split between north/south VA
PARAMETER_CD = "00060"    # discharge (cfs)
YEARS_BACK = 20

# helpers
def fetch_va_dv_chunk(start_date, end_date):
    """
    Fetch daily discharge data for all VA sites within a date range.
    Returns a DataFrame with columns:
        site_no, site_name, date, flow_cfs, lat
    """
    params = {
        "format": "json",
        "stateCd": "VA",
        "parameterCd": PARAMETER_CD,
        "siteType": "ST",
        "siteStatus": "active",
        "startDT": start_date.strftime("%Y-%m-%d"),
        "endDT": end_date.strftime("%Y-%m-%d")
    }
    # fetch data
    print(f"Fetching {start_date.date()} → {end_date.date()} ...")
    resp = requests.get(NWIS_DV_URL, params=params, timeout=60)
    resp.raise_for_status()
    j = resp.json()
    # parse data
    rows = []
    for ts in j.get("value", {}).get("timeSeries", []):
        site_no = ts["sourceInfo"]["siteCode"][0]["value"]
        site_name = ts["sourceInfo"]["siteName"]
        lat = ts["sourceInfo"]["geoLocation"]["geogLocation"]["latitude"]

        for v in ts["values"][0]["value"]:
            val_str = v.get("value")
            if val_str in (None, "", "Ice"):
                continue
            try:
                flow = float(val_str)
            except ValueError:
                continue
            date = v["dateTime"][:10]
            rows.append({
                "site_no": site_no,
                "site_name": site_name,
                "date": date,
                "flow_cfs": flow,
                "lat": lat
            })

    df = pd.DataFrame(rows)
    return df


def fetch_historical_data(years_back=YEARS_BACK, chunk_years=5):
    """
    Fetch historical daily discharge data in multi-year chunks to avoid API limits.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=years_back * 365)

    all_dfs = []
    cur_start = start_date
    while cur_start < end_date:
        cur_end = min(cur_start + timedelta(days=chunk_years * 365), end_date)
        df_chunk = fetch_va_dv_chunk(cur_start, cur_end)
        if not df_chunk.empty:
            all_dfs.append(df_chunk)
        cur_start = cur_end + timedelta(days=1)
        time.sleep(1)  # be nice to the USGS server

    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    else:
        return pd.DataFrame()


def compute_p90_by_day(df):
    """
    Compute 90th percentile discharge per day-of-year per site.
    """
    df["date"] = pd.to_datetime(df["date"])
    df["day_of_year"] = df["date"].dt.dayofyear
    df["north_south"] = df["lat"].apply(lambda x: "north" if x >= LATITUDE_MIDPOINT else "south")

    grouped = (
        df.groupby(["site_no", "site_name", "north_south", "day_of_year"])["flow_cfs"]
        .quantile(0.9)
        .reset_index(name="p90_flow_cfs")
    )
    return grouped


# main
def main():
    print(f"Building historical reference (last {YEARS_BACK} years)...")

    df = fetch_historical_data()
    print(f"Fetched {len(df)} daily flow records total.")

    if df.empty:
        print("No data fetched — exiting.")
        return

    df_p90 = compute_p90_by_day(df)
    df_p90.to_csv(HISTORICAL_FILE, index=False)

    print(f"Saved 90th percentile dataset → {HISTORICAL_FILE}")
    print(f"{len(df_p90)} site-day combinations computed.")


# entry
if __name__ == "__main__":
    main()