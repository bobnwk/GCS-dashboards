import dash
from dash import dcc, html, Input, Output, Dash, callback_context
import pandas as pd
import plotly.express as px
import dash_uploader as du
import os

# Initialize Dash app
app = Dash(__name__)
server = app.server  # Required for deployment
du.configure_upload(app, "./uploads")

# Layout
app.layout = html.Div([
    html.H1("📊 24/7 Support Calls Dashboard", style={"textAlign": "center"}),

    du.Upload(
        id='upload-data',
        text='Drag and Drop or Click to Upload Data',
        max_file_size=1800,
        filetypes=['xlsx'],
        upload_id='data_upload'
    ),

    dcc.Dropdown(
        id='month-selector',
        multi=True,
        placeholder="Select Months"
    ),

    dcc.Graph(id='calls-chart'),
])

# Callback to handle file upload
@app.callback(
    Output('month-selector', 'options'),
    Output('month-selector', 'value'),
    Input('upload-data', 'isCompleted'),
    Input('upload-data', 'fileNames')
)
def load_data(isCompleted, fileNames):
    if not isCompleted or not fileNames:
        return [], []

    file_path = os.path.join("./uploads/data_upload", fileNames[0])

    try:
        global df
        df = pd.read_excel(file_path, sheet_name="first line call")
        df["Call Date"] = pd.to_datetime(df["Call Date"])
        df["Month"] = df["Call Date"].dt.strftime("%Y-%m")

        # Mapping customer names to short codes
        customer_mapping = {
            "NewCold | WHS Piacenza": "PIA",
            "NewCold | WHS Tacoma": "TAC",
            "NewCold | WHS Lebanon": "LEB",
            "NewCold | WHS Atlanta": "ATL"
        }
        df["Customer Short"] = df["Customer (Caller)"].map(customer_mapping)

        months = sorted(df["Month"].unique(), reverse=True)
        return [{'label': month, 'value': month} for month in months], months[:6]

    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return [], []

# Callback to update graph
@app.callback(
    Output('calls-chart', 'figure'),
    Input('month-selector', 'value')
)
def update_chart(selected_months):
    if not selected_months:
        print("❌ No months selected.")
        return px.bar(title="Select a month to display data")

    filtered_df = df[df["Month"].isin(selected_months)]

    # Ensure at least one entry for each customer
    all_customers = ["ATL", "LEB", "PIA", "TAC"]

    # Get top 20 callers
    calls_per_caller = filtered_df["Caller name"].value_counts().head(20)
    top_20_df = filtered_df[filtered_df["Caller name"].isin(calls_per_caller.index)]

    # Group data
    grouped_data = top_20_df.groupby(["Caller name", "Customer Short"]).size().unstack().fillna(0)

    # Add missing customer columns if they don't exist
    for customer in all_customers:
        if customer not in grouped_data.columns:
            grouped_data[customer] = 0

    # Add unjustified calls count
    unjustified_calls = top_20_df[top_20_df["Justified? (24/7)"] == "No"].groupby(["Caller name"]).size()
    grouped_data["Unjustified Calls"] = unjustified_calls.fillna(0)

    # Reset index for visualization
    grouped_data = grouped_data.reset_index()

    print(f"📊 Processed Data for Chart:\n{grouped_data.head()}")

    # Create bar chart
    fig = px.bar(
        grouped_data.melt(id_vars="Caller name", value_vars=["ATL", "LEB", "PIA", "TAC", "Unjustified Calls"]),
        x="Caller name", y="value", color="variable",
        color_discrete_map={"ATL": "blue", "LEB": "yellow", "PIA": "green", "TAC": "purple", "Unjustified Calls": "red"},
        labels={"value": "Number of Calls", "Caller name": "Caller"},
        title=f"Top 20 Callers - {', '.join(selected_months)}"
    )

    return fig

# Run server
if __name__ == '__main__':
    app.run_server(debug=True)
