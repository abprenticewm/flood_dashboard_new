import pandas as pd
import plotly.express as px

DATA_FILE = "data/gauge_data_processed.csv"

# build map
def build_map(df):

    # remove invalid flow values so Plotly doesn't try to size markers with them
    df = df[df["flow_cfs"] >= 0].copy()
    df = df[df["flow_cfs"].notna()]

    fig = px.scatter_map(
        df,
        lat="latitude",
        lon="longitude",
        color="high_flow",
        size="flow_cfs",
        hover_name="site_name",
        hover_data={
            "flow_cfs": True,
            "p90_flow_cfs": True,
            "ratio": True,
            "latitude": False,
            "longitude": False,
        },
        zoom=5,
        height=700,
    )
    fig.update_layout(map_style="open-street-map")
    return fig

# entry
if __name__ == "__main__":
    print("Loading processed gauge data...")
    df = pd.read_csv(DATA_FILE)

    fig = build_map(df)
    fig.show()