import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Output, Input, State
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
# -------------------------------
# Main map page layout (with sidebar)
# -------------------------------
def main_map_layout():
    df = pd.read_csv(DATA_FILE)

    return html.Div([

        # Entire page container
        html.Div([

            # ----------------------- Sidebar -----------------------
            html.Div([

                # Title
                html.H1(
                    "VA Flood Risk Map",
                    style={"textAlign": "center", "marginTop": "10px"}
                ),

                html.Hr(),

                # ----- Description -----
                html.H3("About This Map"),
                html.P(
                    "This dashboard maps current flood risk across Virginia using real-time "
                    "USGS stream gauge data. The newest available data loads automatically "
                    "when the dashboard opens.",
                    style={"fontSize": "14px"}
                ),

                html.Hr(),

                # ----- Refresh button -----
                html.Button(
                    "Refresh Data",
                    id="refresh-btn",
                    n_clicks=0,
                    style={
                        "display": "block",
                        "margin": "10px auto",
                        "padding": "10px 20px",
                        "fontSize": "16px"
                    }
                ),
                html.P(
                    "Click to manually refresh data. Values may not change if USGS has not "
                    "published a newer reading yet.",
                    style={"fontSize": "13px", "textAlign": "center", "marginTop": "5px"}
                ),

                html.Hr(),

                # ----- Legend -----
                html.H3("Legend"),

                html.P("Flow Trend (3-hour % change):", style={"marginBottom": "4px"}),
                html.Ul([
                    html.Li("Brown  — flow stable or decreasing (≤ 0%)"),
                    html.Li("Blue  — rising moderately (0% to 25%)"),
                    html.Li("Red  — sharp rise (> 25%)"),
                ], style={"fontSize": "13px"}),

                html.Br(),

                html.P("Flow in cubic feet per second (cfs):", style={"marginBottom": "4px"}),
                html.Ul([
                    html.Li("Small dot — 0 to 50 cfs"),
                    html.Li("Medium dot — 51 to 200 cfs"),
                    html.Li("Large dot — above 200 cfs")
                ], style={"fontSize": "13px"}),

                html.Hr(),

                # ----- Instructions -----
                html.H3("How to Use"),
                html.Ul([
                    html.Li("Hover a gauge to view summary statistics."),
                    html.Li("Click a gauge to open a detailed page with more data."),
                ], style={"fontSize": "13px"}),

            ],
            style={
                "width": "20%",
                "minWidth": "200px",
                "background": "#f3f3f3",
                "padding": "15px",
                "overflowY": "auto",
                "boxSizing": "border-box"
            }),

            # ----------------------- Map Section -----------------------
            html.Div([
                dcc.Graph(
                    id="map-graph",
                    figure=build_map(df),
                    style={"height": "100%", "width": "100%"}
                )
            ],
            style={
                "flex": "1",
                "display": "flex",
                "flexDirection": "column",
                "overflow": "hidden"
            }),

        ],
        style={
            "display": "flex",
            "height": "100vh",
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

        # Read the full main metadata file
        df_main = pd.read_csv(DATA_FILE)
        site_no = df_main.loc[site_id]["site_no"]
        site_name = df_main.loc[site_id]["site_name"]

        # Read full time-series CSV (DO NOT modify -9999 here)
        ts = pd.read_csv("data/gauge_data.csv")
        ts["timestamp_utc"] = pd.to_datetime(ts["timestamp_utc"])

        # Filter to this gauge only
        gauge_df = ts[ts["site_no"] == site_no].sort_values("timestamp_utc")

        # 6-hour window
        if not gauge_df.empty:
            latest_time = gauge_df["timestamp_utc"].max()
            cutoff = latest_time - pd.Timedelta(hours=6)
            gauge_6h = gauge_df[gauge_df["timestamp_utc"] >= cutoff]
        else:
            gauge_6h = gauge_df.copy()

        # Build 6-hour graph
        fig = px.line(
            gauge_6h,
            x="timestamp_utc",
            y="flow_cfs",
            title=f"Last 6 Hours — {site_name}",
            labels={"timestamp_utc": "Time (UTC)", "flow_cfs": "Flow (cfs)"}
        )

        fig.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20))

        return html.Div([

            # -----------------------------
            # Page Title
            # -----------------------------
            html.H1(
                f"{site_name}",
                style={"textAlign": "center", "marginTop": "15px"}
            ),
            
            # -----------------------------
            # Site Info – centered below gauge title
            # -----------------------------
            html.Div(
                style={
                    "textAlign": "center",
                    "fontWeight": "bold",
                    "marginBottom": "15px",
                    "fontSize": "15px",
                },
                children=f"Site {df_main.loc[site_id]['site_no']} | Lat: {df_main.loc[site_id]['latitude']}° | Lon: {df_main.loc[site_id]['longitude']}°"
            ),

            # -----------------------------
            # Main stats area – compact and pretty
            # -----------------------------
            html.Div(
                style={
                    "display": "flex",
                    "flexDirection": "row",
                    "alignItems": "flex-start",
                    "gap": "20px",
                    "marginBottom": "25px",
                    "flexWrap": "wrap",
                },
                children=[

                    # Left side: ROC and High Flow side by side
                    html.Div(
                        style={
                            "display": "flex",
                            "flexDirection": "row",
                            "gap": "20px",
                            "flex": "0 0 auto",
                            "alignItems": "flex-start",
                        },
                        children=[

                            # Rate of Change
                            html.Div(
                                style={
                                    "fontSize": "16px",
                                    "lineHeight": "1.2",
                                },
                                children=[
                                    html.H4("Rate of Change (%)", style={"color": "#5A4A2F", "marginBottom": "5px"}),
                                    html.P(f"1h: {df_main.loc[site_id]['pct_change_1h']:.1f}%", style={"margin": "2px 0"}),
                                    html.P(f"3h: {df_main.loc[site_id]['pct_change_3h']:.1f}%", style={"margin": "2px 0"}),
                                    html.P(f"6h: {df_main.loc[site_id]['pct_change_6h']:.1f}%", style={"margin": "2px 0"}),
                                ]
                            ),

                            # High Flow / Flow Rate
                            html.Div(
                                style={
                                    "fontSize": "16px",
                                    "lineHeight": "1.2",
                                },
                                children=[
                                    html.H4("High Flow", style={"color": "#5A4A2F", "marginBottom": "5px"}),
                                    html.P(
                                        f"Status: {'HIGH FLOW' if df_main.loc[site_id]['flow_cfs'] >= df_main.loc[site_id]['p90_flow_cfs'] else 'Normal'}",
                                        style={"margin": "2px 0"}
                                    ),
                                    html.P(f"Threshold (90th percentile): {df_main.loc[site_id]['p90_flow_cfs']} cfs", style={"margin": "2px 0"}),
                                ]
                            ),
                        ]
                    ),

                    # Vertical brown line separator
                    html.Div(
                        style={
                            "width": "2px",
                            "backgroundColor": "#A18F65",
                            "alignSelf": "stretch",
                        }
                    ),

                    # Explanation area (right, bigger)
                    html.Div(
                        style={
                            "flex": "1",
                            "minWidth": "300px",
                            "fontSize": "15px",
                            "lineHeight": "1.5",
                        },
                        children=[
                            html.H4("Explanation", style={"color": "#5A4A2F", "marginBottom": "10px"}),
                            html.P([
                                html.B("Rate of Change"), 
                                " compares the current flow to previous measurements (1h, 3h, 6h)."
                            ], style={"marginBottom": "5px"}),
                            html.P([
                                "The ", html.B("90th percentile high flow threshold"), 
                                " is calculated from ~20 years of historical USGS data for this calendar day. "
                                "If the current flow exceeds this threshold, the gauge is classified as HIGH FLOW."
                            ], style={"marginBottom": "5px"}),
                        ]
                    )
                ]
            ),

            # -----------------------------
            # 6-hour Graph
            # -----------------------------
            dcc.Graph(
                id="gauge-timeseries",
                figure=fig,
                style={"width": "90%", "margin": "0 auto"}
            ),

            # -----------------------------
            # Download Buttons
            # -----------------------------
            html.Button(
                "Download 6h Graph (PNG)",
                id="download-graph-btn",
                n_clicks=0,
                style={
                    "margin": "10px auto",
                    "display": "block",
                    "padding": "10px 20px",
                    "fontSize": "16px"
                }
            ),

            html.Button(
                "Download Full CSV (24hr Data for Site)",
                id="download-fullcsv-btn",
                n_clicks=0,
                style={
                    "margin": "10px auto",
                    "display": "block",
                    "padding": "10px 20px",
                    "fontSize": "16px"
                }
            ),

            dcc.Download(id="download-graph-file"),
            dcc.Download(id="download-fullcsv-file"),

            html.Br(),

           
            # -----------------------------
            # Notes Section (Two Styled Boxes)
            # -----------------------------
            html.Div([

                # Box 1 – Missing Data
                html.Div([
                    html.H4("Missing Data"),
                    html.P(
                        "Missing data is recorded by the USGS as -9999. In data downloads this "
                        "number is preserved. In graphs, missing data is converted to NaN and "
                        "appears as a break in the plotted line."
                    )
                ],
                style={
                    "border": "2px solid #A18F65",
                    "borderRadius": "8px",
                    "padding": "12px",
                    "margin": "10px",
                    "flex": "1",
                    "background": "#fdfbf7"
                }),

                # Box 2 – Negative Flow
                html.Div([
                    html.H4("Negative Flow"),
                    html.P(
                        "Negative flow rates can occur in tidal areas where water reverses "
                        "direction during high tide and temporarily flows upstream."
                    )
                ],
                style={
                    "border": "2px solid #A18F65",
                    "borderRadius": "8px",
                    "padding": "12px",
                    "margin": "10px",
                    "flex": "1",
                    "background": "#fdfbf7"
                })

            ],
            style={
                "display": "flex",
                "flexDirection": "row",
                "justifyContent": "space-between",
                "width": "90%",
                "margin": "20px auto",
                "flexWrap": "wrap"
            })

        ])




    else:
        return html.H1("404: Page not found")
    
#generate file names for dowloads 
def unique_filename(base_name, ext):
    """Generate unique filename in download_data/ with counter."""
    folder = "download_data"
    os.makedirs(folder, exist_ok=True)

    date_str = pd.Timestamp.utcnow().strftime("%Y%m%d")
    n = 1
    while True:
        filename = f"{base_name}_{date_str}_{n}.{ext}"
        path = os.path.join(folder, filename)
        if not os.path.exists(path):
            return path
        n += 1


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

#dowload call backs 
@app.callback(
    Output("download-graph-file", "data"),
    Input("download-graph-btn", "n_clicks"),
    State("gauge-timeseries", "figure"),
    State("url", "pathname"),
    prevent_initial_call=True
)
def download_graph(n_clicks, fig, pathname):
    site_id = int(pathname.split("/")[-1])

    df_main = pd.read_csv(DATA_FILE)
    site_name = df_main.loc[site_id]["site_name"].replace(" ", "_")

    filepath = unique_filename(site_name, "png")

    import plotly.io as pio
    pio.write_image(fig, filepath, scale=2)

    return dcc.send_file(filepath)

@app.callback(
    Output("download-fullcsv-file", "data"),
    Input("download-fullcsv-btn", "n_clicks"),
    State("url", "pathname"),
    prevent_initial_call=True
)

def download_full_csv(n_clicks, pathname):
    site_id = int(pathname.split("/")[-1])

    df_main = pd.read_csv(DATA_FILE)
    site_no = df_main.loc[site_id]["site_no"]
    site_name = df_main.loc[site_id]["site_name"].replace(" ", "_")

    ts = pd.read_csv("data/gauge_data.csv")
    ts["timestamp_utc"] = pd.to_datetime(ts["timestamp_utc"])

    # Filter NO -9999 changes here
    gauge_df = ts[ts["site_no"] == site_no].sort_values("timestamp_utc")

    filepath = unique_filename(site_name, "csv")
    gauge_df.to_csv(filepath, index=False)

    return dcc.send_file(filepath)


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