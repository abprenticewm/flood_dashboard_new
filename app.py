import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Output, Input
import webbrowser
from threading import Timer
import os
import numpy as np

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
        custom_data=[
            "site_id",
            "site_name",
            "flow_cfs",
            "p90_flow_cfs",
            "ratio",
            "pct_change_3h"
        ],
        zoom=6,
        center={"lat": center_lat, "lon": center_lon},
        height=700,
        color_discrete_map={
            "#A18F65": "#A18F65",
            "#942719": "#942719",
            "#5279A8": "#5279A8"
        }
    )

    fig.update_layout(showlegend=False)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
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
# Main map page layout (with sidebar)
# -------------------------------
def main_map_layout():
    df = pd.read_csv(DATA_FILE)

    return html.Div([
        # Whole page container
        html.Div([
            # ---- Sidebar ----
            html.Div([
                # Dashboard title
                html.H1("VA Flood Risk Map", style={"textAlign": "center", "marginTop": "10px"}),

                html.Hr(),

                # Refresh button
                html.Button(
                    "Refresh Data",
                    id="refresh-btn",
                    n_clicks=0,
                    style={
                        "display": "block",
                        "margin": "10px auto",
                        "padding": "10px 20px",
                        "fontSize": "16px",
                    }
                ),

                # Placeholder for future sidebar content
                html.P("Add legend or explanations here later.")
            ],
            style={
                "width": "20%",
                "minWidth": "180px",
                "background": "#f3f3f3",
                "padding": "15px",
                "overflowY": "auto",  # sidebar scrolls if content too long
                "boxSizing": "border-box"
            }),

            # ---- Map area ----
            html.Div([
                # MAP fills all remaining vertical space
                dcc.Graph(
                    id="map-graph",
                    figure=build_map(df),
                    style={"height": "100%", "width": "100%"}
                )
            ],
            style={
                "flex": "1",             # take remaining width
                "display": "flex",
                "flexDirection": "column",
                "overflow": "hidden"
            }),
        ],
        style={
            "display": "flex",
            "height": "100vh",  # full viewport height
            "overflow": "hidden"
        })
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

        # Read CSV (time series)
        df = pd.read_csv("data/gauge_data.csv")

        # Fix -9999 to nan
        df["flow_cfs"] = df["flow_cfs"].replace(-9999, np.nan)

        # Convert timestamp
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])

        # Get this gauge's site_no
        df_main = pd.read_csv(DATA_FILE)  # main file with metadata
        site_no = df_main.loc[site_id]["site_no"]
        site_name = df_main.loc[site_id]["site_name"]

        # Filter time series
        gauge_df = df[df["site_no"] == site_no].sort_values("timestamp_utc")

        # Last 6 hours only
        if not gauge_df.empty:
            latest_time = gauge_df["timestamp_utc"].max()
            cutoff = latest_time - pd.Timedelta(hours=6)
            gauge_df = gauge_df[gauge_df["timestamp_utc"] >= cutoff]

        # Build time series figure
        fig = px.line(
            gauge_df,
            x="timestamp_utc",
            y="flow_cfs",
            title=f"Last 6 Hours — {site_name}",
            labels={"timestamp_utc": "Time (UTC)", "flow_cfs": "Flow (cfs)"}
        )

        fig.update_layout(
            height=500,
            margin=dict(l=20, r=20, t=40, b=20)
        )

        return html.Div([
            html.H1(f"Gauge: {site_name}", style={"textAlign": "center"}),

            dcc.Graph(
                id="gauge-timeseries",
                figure=fig,
                style={"width": "90%", "margin": "0 auto"}
            ),

            html.Br(),

            html.Ul([
                html.Li(f"Site Number: {site_no}"),
                html.Li(f"Most Recent Flow: {df_main.loc[site_id]['flow_cfs']} cfs"),
                html.Li(f"P90 Flow: {df_main.loc[site_id]['p90_flow_cfs']} cfs"),
                html.Li(f"Percent of P90: {df_main.loc[site_id]['ratio']*100:.1f}%"),
                html.Li(f"3h Percent Change: {df_main.loc[site_id]['pct_change_3h']}")
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