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

    # Color based on pct_change_3h using hex codes
    def color_logic(x):
        if x <= 0:
            return "#A18F65"  # brown
        elif x > 25:
            return "#942719"  # red
        else:
            return "#5279A8"  # blue
    df["color_group"] = df["pct_change_3h"].apply(color_logic)

    # Size classes based on flow
    def size_class(flow):
        if flow <= 50:
            return 10
        elif flow <= 200:
            return 20
        else:
            return 30
    df["size_class"] = df["flow_cfs"].apply(size_class)

    # Calculate center for initial zoom
    center_lat = df["latitude"].mean()
    center_lon = df["longitude"].mean()

    # Scatter map
    fig = px.scatter_map(
        df,
        lat="latitude",
        lon="longitude",
        color="color_group",
        size="size_class",
        hover_name="site_name",
        hover_data={
            "flow_cfs": True,
            "p90_flow_cfs": True,
            "ratio": True,
            "pct_change_3h": True,
            "latitude": False,
            "longitude": False
        },
        custom_data=["site_id", "site_name", "flow_cfs", "p90_flow_cfs", "ratio", "pct_change_3h"],
        zoom=6,  # zoomed-in view
        center={"lat": center_lat, "lon": center_lon},
        height=700,
        color_discrete_map={
            "#A18F65": "#A18F65",
            "#942719": "#942719",
            "#5279A8": "#5279A8"
        }
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
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/':
        return main_map_layout()
    elif pathname.startswith('/gauge/'):
        site_id = int(pathname.split('/')[-1])
        df = pd.read_csv(DATA_FILE)
        gauge_row = df.loc[site_id]
        return html.Div([
            html.H1(f"Gauge: {gauge_row['site_name']}", style={"textAlign": "center"}),
            html.Br(),
            html.Ul([
                html.Li(f"Flow (cfs): {gauge_row['flow_cfs']}"),
                html.Li(f"P90 Flow (cfs): {gauge_row['p90_flow_cfs']}"),
                html.Li(f"Percent of P90: {gauge_row['ratio']*100:.1f}%"),
                html.Li(f"3h Percent Change: {gauge_row['pct_change_3h']}")
            ])
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
        # Simple direct indexing
        site_id = clickData['points'][0]['customdata'][0]
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
