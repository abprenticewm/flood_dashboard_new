import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Output, Input
import webbrowser
from threading import Timer
import os

DATA_FILE = "data/gauge_data_processed.csv"

# build map
def build_map(df):
    df = df[df["flow_cfs"] >= 0].copy()
    df = df[df["flow_cfs"].notna()]

    # hover text
    df["hover_text"] = (
        "Flow: " + df["flow_cfs"].round(1).astype(str) + " cfs<br>" +
        "P90 Flow: " + df["p90_flow_cfs"].round(1).astype(str) + " cfs<br>" +
        "Percent of P90: " + (df["ratio"]*100).round(1).astype(str) + "%"
    )
    # add map components
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
    return fig

# dash app
app = Dash(__name__)
app.layout = html.Div([
    # header
    html.H1("Flood Gauge Dashboard", style={"textAlign": "center"}),
    html.Div(
        html.Button("Refresh Data", id="refresh-btn", n_clicks=0, style={
            "display": "block",
            "margin": "10px auto",
            "padding": "10px 20px",
            "fontSize": "16px",
        }),
        style={"textAlign": "center"}
    ),
    dcc.Graph(id="map-graph", figure=build_map(pd.read_csv(DATA_FILE)))
])

# callback to refresh map using button
@app.callback(
    Output("map-graph", "figure"),
    Input("refresh-btn", "n_clicks")
)
def update_map(n_clicks):
    print(f"Refresh clicked {n_clicks} times")
    df = pd.read_csv(DATA_FILE)
    return build_map(df)

# open browser automatically
def open_browser():
    webbrowser.open_new("http://127.0.0.1:8050/")

# main entry point
if __name__ == "__main__":
    # Only open browser if not a reloader process
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        Timer(1, open_browser).start()
    app.run(debug=True, port=8050)