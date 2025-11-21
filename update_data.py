# update_pipeline_import.py
import os
import pandas as pd
from datetime import datetime

# Import the main functions
from fetch_data import main as fetch_data_main
from compare_p90_roc import main as p90_rate_of_change_main
# from compare_to_p90 import main as compare_main
from fetch_historical import main as historical_main  # Make sure filename matches

LOG_FILE = "update_log.csv"
MAX_LOG_RECORDS = 100

def log_update():
    """Append an update timestamp and keep only the last 100 records."""
    timestamp = datetime.utcnow()
    if os.path.exists(LOG_FILE):
        df_log = pd.read_csv(LOG_FILE)
    else:
        df_log = pd.DataFrame(columns=["timestamp_utc"])
    
    df_log = pd.concat([df_log, pd.DataFrame({"timestamp_utc": [timestamp]})], ignore_index=True)
    df_log = df_log.tail(MAX_LOG_RECORDS)
    df_log.to_csv(LOG_FILE, index=False)
    print(f"✅ Logged update at {timestamp}")

def historical_check():
    """Check if historical data exists; if not, fetch it."""
    hist_file = "data/historical_p90.csv"
    if not os.path.exists(hist_file) or os.path.getsize(hist_file) == 0:
        print("Historical data missing — fetching...")
        historical_main()
    else:
        print("Historical data already exists.")

def update():
    """Fetch latest data and run analyses."""
    print("Starting update process...")
    fetch_data_main()
    p90_rate_of_change_main()
    # compare_main()
    log_update()
    print("Update process complete.\n")

def main():
    historical_check()
    update()

if __name__ == "__main__":
    main()
