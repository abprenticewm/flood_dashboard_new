import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Output, Input
import webbrowser
from threading import Timer
import os

DATA_FILE = "data/gauge_data_processed.csv"

# -------------------------------
# Build the map figure
# -------------------------------
def build_map(df):
    df = df[df["flow_cfs"] >= 0].copy()
    df = df[df["flow_cfs"].notna()]

    # Assign unique ID for each gauge
    df["site_id"] = df.index

    # Scatter map
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
            "longitude": False
        },
        custom_data=["site_id", "site_name", "flow_cfs", "p90_flow_cfs", "ratio"],  # all info we need
        zoom=5,
        height=700,
    )

    return fig

# -------------------------------
# Dash app
# -------------------------------
app = Dash(__name__, suppress_callback_exceptions=True)
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# -------------------------------
# Main map page layout
# -------------------------------
def main_map_layout():
    df = pd.read_csv(DATA_FILE)
    return html.Div([
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
        dcc.Graph(id="map-graph", figure=build_map(df))
    ])

# -------------------------------
# Page routing
# -------------------------------
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
    Input('url', 'search')
)
def display_page(pathname, search):
    if pathname == '/':
        return main_map_layout()
    elif pathname.startswith('/gauge/'):
        # Extract info from URL query string if you prefer, or you can pass state
        return html.Div([
            html.H1(f"Gauge Info Page", style={"textAlign": "center"}),
            html.Div("This page will show the clicked gauge info.")
        ])
    else:
        return html.H1("404: Page not found")

# -------------------------------
# Refresh map callback
# -------------------------------
@app.callback(
    Output("map-graph", "figure"),
    Input("refresh-btn", "n_clicks")
)
def update_map(n_clicks):
    df = pd.read_csv(DATA_FILE)
    return build_map(df)

# -------------------------------
# Click on gauge -> navigate
# -------------------------------
@app.callback(
    Output('url', 'pathname'),
    Input('map-graph', 'clickData'),
    prevent_initial_call=True
)
def go_to_gauge(clickData):
    if clickData:
        # Directly access customdata by index
        site_id = clickData['points'][0]['customdata'][0]
        site_name = clickData['points'][0]['customdata'][1]
        flow = clickData['points'][0]['customdata'][2]
        p90 = clickData['points'][0]['customdata'][3]
        ratio = clickData['points'][0]['customdata'][4]

        # Navigate to gauge page using site_id
        return f'/gauge/{site_id}'
    return '/'

# -------------------------------
# Auto open browser
# -------------------------------
def open_browser():
    webbrowser.open_new("http://127.0.0.1:8050/")

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        Timer(1, open_browser).start()
    app.run(debug=True, port=8050)
