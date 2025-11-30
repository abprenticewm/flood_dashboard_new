# update_pipeline.py

import subprocess
import sys
import os  # <-- needed for file check

HISTORICAL_FILE = os.path.join("data", "historical_p90.csv")

def run(script):
    print(f"\nRunning {script}...")
    r = subprocess.run([sys.executable, script])
    if r.returncode != 0:
        print(f"Error running {script}")
    else:
        print(f"Finished {script}")

def main():
    # fetch last 24h readings (incremental)
    run("fetch_data.py")

    # make sure historical file exists
    if not os.path.exists(HISTORICAL_FILE):
        run("fetch_historical.py")
    else:
        print(f"{HISTORICAL_FILE} already exists, skipping historical fetch.")

    # process into dashboard-ready CSV
    run("process_gauge_data.py")

# entry
if __name__ == "__main__":
    main()
