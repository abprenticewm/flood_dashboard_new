# update_pipeline.py

import subprocess
import sys

def run(script):
    print(f"\n Running {script}...")
    r = subprocess.run([sys.executable, script])
    if r.returncode != 0:
        print(f"Error running {script}")
    else:
        print(f"Finished {script}")

def main():
    # fetch last 24h readings (incremental)
    run("fetch_data.py")

    # make sure historical file exists
    run("fetch_historical.py")

    # process into dashboard-ready CSV
    run("process_gauge_data.py")

# entry
if __name__ == "__main__":
    main()