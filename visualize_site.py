##NOT WORKING YET 

# visualize.py - Plot streamflow for a given site
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# ------------------------------
# CONFIG
# ------------------------------
DATA_DIR = Path("data")
NORTH_FILE = DATA_DIR / "north_va.csv"
SOUTH_FILE = DATA_DIR / "south_va.csv"
PLOTS_DIR = Path("plots")
PLOTS_DIR.mkdir(exist_ok=True, parents=True)

# ------------------------------
# HELPER FUNCTIONS
# ------------------------------
def load_data(site_name_or_no):
    """Load CSV containing the site, return DataFrame and region"""
    for file_path, region in [(NORTH_FILE, "north"), (SOUTH_FILE, "south")]:
        if file_path.exists():
            df = pd.read_csv(file_path)
            df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
            mask = (df["site_name"] == site_name_or_no) | (df["site_no"] == site_name_or_no)
            df_site = df[mask]
            if not df_site.empty:
                return df_site.sort_values("timestamp_utc"), region
    return pd.DataFrame(), None

def plot_site(df, site_name_or_no, region):
    """Plot flow for a site"""
    plt.figure(figsize=(12,6))
    plt.plot(df["timestamp_utc"], df["flow_cfs"], marker='o', linestyle='-', label="Flow (cfs)")
    plt.title(f"Streamflow - {site_name_or_no} ({region})")
    plt.xlabel("Timestamp (UTC)")
    plt.ylabel("Flow (cfs)")
    plt.legend()
    plt.grid(True)

    # Save plot
    plot_file = PLOTS_DIR / f"{site_name_or_no}_flow_plot.png"
    plt.tight_layout()
    plt.savefig(plot_file)
    plt.close()
    print(f"✅ Plot saved to {plot_file}")

# ------------------------------
# MAIN
# ------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python visualize.py <site_name_or_no>")
        return

    site_name_or_no = sys.argv[1]
    df_site, region = load_data(site_name_or_no)
    
    if df_site.empty:
        print(f"⚠️ Site '{site_name_or_no}' not found in north_va.csv or south_va.csv")
        return

    plot_site(df_site, site_name_or_no, region)

if __name__ == "__main__":
    main()
