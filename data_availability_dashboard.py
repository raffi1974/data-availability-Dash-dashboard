# --- Import Necessary Libraries ---
# pandas is for data manipulation (reading Excel, creating DataFrames).
# dash is the main framework for building the web application.
# dcc (Dash Core Components) and html provide the building blocks for the app's layout (e.g., dropdowns, graphs, text).
# Input and Output are used to make the dashboard interactive.
# plotly.express is used for creating the charts.
# subprocess, sys, and os are used for the helper function that installs required libraries.
import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import subprocess
import sys
import os

# --- Installation of Required Libraries ---
# This function checks if a 'requirements.txt' file exists and, if so, uses pip to install all the libraries listed in it.
# This makes setup easier, as you only need to run this one script.
def install_requirements():
    """Installs packages from requirements.txt using pip."""
    try:
        print("Checking and installing dependencies...")
        # This command runs 'pip install -r requirements.txt' in the terminal.
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies are all set.")
    except subprocess.CalledProcessError as e:
        # If the installation fails, it prints an error and stops the script.
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

# This checks if the file exists in the current folder before trying to run the installation.
if os.path.exists("requirements.txt"):
    install_requirements()
else:
    print("requirements.txt not found. Please ensure it's in the same directory.")

# --- User Input Section ---
# ACTION NEEDED: Update these variables if your file name or sheet names are different.
EXCEL_FILE_PATH = 'C:/Users/511232/Desktop/DSS/DATA AVAILABILITY INTERACTIVE DASHBOARD/data.xlsx'  # The name of your Excel file. Must be in the same folder as this script.
DATA_SHEET_NAME = 'data'  # The name of the sheet containing the main dataset.
CRITERIA_SHEET_NAME = 'criteria'  # The name of the sheet with the availability criteria.

# --- 1. Data Loading and Preparation ---
def load_data(file_path, data_sheet, criteria_sheet):
    """Loads data from the specified Excel file and sheets."""
    try:
        # Read the two specified sheets from the Excel file into pandas DataFrames.
        df_main = pd.read_excel(file_path, sheet_name=data_sheet)
        df_criteria = pd.read_excel(file_path, sheet_name=criteria_sheet)
        print("Data loaded successfully.")
    except FileNotFoundError:
        # Handle the error if the Excel file cannot be found.
        print(f"Error: The file '{file_path}' was not found.")
        return None, None
    except ValueError as e:
        # Handle the error if one of the sheet names is incorrect.
        print(f"Error: A sheet was not found. Details: {e}")
        return None, None
    return df_main, df_criteria

# Call the function to load the data.
df, criteria = load_data(EXCEL_FILE_PATH, DATA_SHEET_NAME, CRITERIA_SHEET_NAME)

# If data loading failed (e.g., file not found), stop the script.
if df is None or criteria is None:
    sys.exit("Exiting due to data loading errors.")

# Convert the criteria DataFrame into a dictionary for fast lookups.
# Example: {'Population estimates': 7, 'Registered marriages': 5}
criteria_dict = criteria.set_index('Indicator')['number of years'].to_dict()

# Define the list of columns that are considered for disaggregation.
disaggregation_cols = ['Age', 'group', 'Area', 'Sex', 'Nationality']

# --- 2. Availability Calculation ---
# This section dynamically determines which disaggregations are relevant for each indicator.

'''The logic will be updated so that for a given indicator, a disaggregation column (like 'Age' or 'Sex') 
will only be used in the analysis if it contains valid data (i.e., values other than null or "Not applicable").
 If a column doesn't meet this criteria for an indicator, it will be ignored for that indicator's grouping,
  and the output will reflect that it was not disaggregated.'''

# Create an empty list to store the results of the analysis for each group.
availability_results = []
# Get a list of all unique indicators from the main DataFrame.
unique_indicators = df['Indicator'].unique()

# Loop through each unique indicator to process it individually.
for indicator_name in unique_indicators:
    # Create a temporary DataFrame containing only the data for the current indicator.
    df_indicator = df[df['Indicator'] == indicator_name].copy()
    
    # Identify which disaggregation columns are actually used for this specific indicator.
    valid_disaggregation_cols = []
    for col in disaggregation_cols:
        # A column is considered "valid" if it contains at least one value that is not empty and not the text 'Not applicable'.
        if df_indicator[col].notna().any() and (df_indicator[col].astype(str) != 'Not applicable').any():
            valid_disaggregation_cols.append(col)
    
    # The columns to group by will be the indicator itself, plus any valid disaggregation columns found.
    grouping_cols = ['Indicator'] + valid_disaggregation_cols
    # Group the indicator's data by these columns to create unique combinations.
    grouped_indicator = df_indicator.groupby(grouping_cols)
    
    '''Let's imagine for the indicator "Population estimates", the code found that 'Sex' and 'Area' were the only valid disaggregations.

    The grouping_cols list would be ['Indicator', 'Sex', 'Area'].
    df_indicator.groupby(...) would create groups for every unique combination of these three columns.

    Iteration 1: A Multi-Column Group
    name would be a tuple: ('Population estimates', 'Male', 'Beirut')
    group would be a DataFrame containing only the rows where the Indicator is "Population estimates", Sex is "Male", and Area is "Beirut".
    In this case, isinstance(name, tuple) is True, so the if statement is skipped. The name is already in the format we need.

    Now, let's consider a different indicator, "Total number of refugees", and imagine that for this indicator, no disaggregation columns are valid.
    The grouping_cols list would just be ['Indicator'].
    df_indicator.groupby(...) would create only one group, covering all rows for this indicator.

    Iteration 2: A Single-Column Group
    name would be a string: 'Total number of refugees'
    group would be a DataFrame containing all rows for the "Total number of refugees" indicator.
    In this case, isinstance(name, tuple) is False. The code inside the if block now runs.
    name = (name,) converts the string 'Total number of refugees' into a single-item tuple: ('Total number of refugees',).

    Why is This Normalization Necessary?
    The purpose of this code is to make the next line, group_values = dict(zip(grouping_cols, name)), work reliably every single time.

    The zip function combines two lists. If name was sometimes a tuple and sometimes a string, zip would behave differently and could cause errors. By ensuring name is always a tuple, we can write simple, consistent code that works for both single-column and multi-column groups without needing extra if/else logic later on. It's a technique to make the code more robust and readable.'''

    # Now, loop through each unique group that was created.
    for name, group in grouped_indicator:
        # Standardize the 'name' of the group to always be a tuple, for consistency.
        if not isinstance(name, tuple):
            name = (name,)
        
        # Create a dictionary of the values that define this specific group.
        # Example: {'Indicator': 'Population estimates', 'Sex': 'Male', 'Area': 'Beirut'}
        group_values = dict(zip(grouping_cols, name))
        
        # Count the number of non-empty 'Value' entries to find the number of available years.
        valid_years_count = group['Value'].notna().sum()
        # Look up the required number of years from the criteria dictionary.
        required_years = criteria_dict.get(indicator_name, float('inf'))
        # Determine if the data is "Available" or "Not Available" based on the criteria.
        is_available = "Available" if valid_years_count >= required_years else "Not Available"
        
        # Build a dictionary to hold the results for this specific group.
        result_row = {
            'Indicator': indicator_name,
            'Number of Years Required': required_years,
            'Number of Years Available': valid_years_count,
            'Availability': is_available
        }
        # Add the disaggregation values to the result row.
        # If a column was not used for grouping, mark it as 'N/A (Not Disaggregated)'.
        for col in disaggregation_cols:
            result_row[col] = group_values.get(col, 'N/A (Not Disaggregated)')
        # Add the completed row to our list of results.
        availability_results.append(result_row)

# Convert the list of result dictionaries into a final pandas DataFrame. This will be the main data source for the dashboard.
df_availability = pd.DataFrame(availability_results)

# --- 3. Dashboard Layout ---
# Initialize the Dash application.
app = dash.Dash(__name__)
# This line is crucial for deployment to services like Render. It exposes the underlying Flask server.
server = app.server

# Define the layout of the web page using Dash HTML components.
app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'padding': '20px'}, children=[
    
    # The main title of the dashboard.
    html.H1("Data Availability Dashboard", style={'textAlign': 'center', 'color': '#333'}),
    html.Hr(),
    
    # A container for all the filter controls.
    html.Div([
        # Filter for the 'Indicator' column.
        html.Div([
            html.Label("Filter by Indicator:"),
            dcc.Dropdown(id='indicator-filter', options=[{'label': i, 'value': i} for i in df_availability['Indicator'].unique()], multi=True, placeholder="Select Indicators..."),
        ], style={'width': '48%', 'display': 'inline-block', 'paddingRight': '2%'}),
        
        # Filter for the 'Availability' status.
        html.Div([
            html.Label("Filter by Availability:"),
            dcc.Dropdown(id='availability-filter', options=[{'label': 'Available', 'value': 'Available'}, {'label': 'Not Available', 'value': 'Not Available'}], multi=True, placeholder="Select Availability Status..."),
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        # This creates a dropdown filter for each of the disaggregation columns automatically.
        html.Div([
            dcc.Dropdown(id=f'{col}-filter', options=[{'label': i, 'value': i} for i in df_availability[col].dropna().unique()], multi=True, placeholder=f"Filter by {col}...") for col in disaggregation_cols
        ], style={'marginTop': '15px'})
        
    ], style={'marginBottom': '20px', 'padding': '15px', 'border': '1px solid #ddd', 'borderRadius': '5px'}),
    
    # A container for the charts.
    html.Div([
        # The pie chart will be displayed here. It's an empty graph component that will be updated by the callback.
        dcc.Graph(id='availability-pie-chart', style={'width': '48%', 'display': 'inline-block'}),
        # The bar chart will be displayed here.
        dcc.Graph(id='indicator-bar-chart', style={'width': '48%', 'display': 'inline-block'}),
    ]),
    
    # The title for the data table.
    html.H3("Detailed Availability Data", style={'marginTop': '30px'}),
    # The interactive data table.
    dash_table.DataTable(
        id='availability-table',
        columns=[{"name": i, "id": i} for i in df_availability.columns], # Define columns from the DataFrame.
        data=df_availability.to_dict('records'), # The initial data for the table.
        page_size=15, # Show 15 rows per page.
        style_table={'overflowX': 'auto'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        style_cell={'padding': '10px', 'textAlign': 'left'},
        filter_action="native", # Allow filtering within the table itself.
        sort_action="native", # Allow sorting within the table.
    )
])

# --- 4. Callbacks for Interactivity ---
# This is the "brain" of the dashboard. It connects the filters (Inputs) to the graphs and table (Outputs).
@app.callback(
    # The outputs that will be updated when the function runs.
    [Output('availability-table', 'data'),
     Output('availability-pie-chart', 'figure'),
     Output('indicator-bar-chart', 'figure')],
    # The inputs that will trigger the function whenever their value changes.
    [Input('indicator-filter', 'value'),
     Input('availability-filter', 'value')] +
    [Input(f'{col}-filter', 'value') for col in disaggregation_cols]
)
def update_dashboard(selected_indicators, selected_availability, *filters):
    # Start with a fresh copy of the full results DataFrame.
    filtered_df = df_availability.copy()
    
    # Apply each filter if a value has been selected by the user.
    if selected_indicators:
        filtered_df = filtered_df[filtered_df['Indicator'].isin(selected_indicators)]
    if selected_availability:
        filtered_df = filtered_df[filtered_df['Availability'].isin(selected_availability)]
    # Loop through the disaggregation filters.
    for i, col in enumerate(disaggregation_cols):
        if filters[i]:
            filtered_df = filtered_df[filtered_df[col].isin(filters[i])]

    # Create the pie chart using the filtered data.
    pie_chart_figure = px.pie(filtered_df, names='Availability', title='Overall Data Availability', color='Availability', color_discrete_map={'Available':'#2ca02c', 'Not Available':'#d62728'})
    
    # Summarize the data to create the bar chart.
    indicator_summary = filtered_df.groupby(['Indicator', 'Availability']).size().reset_index(name='Count')
    bar_chart_figure = px.bar(indicator_summary, x='Indicator', y='Count', color='Availability', title='Availability by Indicator', barmode='group', color_discrete_map={'Available':'#2ca02c', 'Not Available':'#d62728'})
    
    # Return the updated data and figures to the output components in the layout.
    return filtered_df.to_dict('records'), pie_chart_figure, bar_chart_figure

# --- 5. Run the Application ---
# This block of code will only run when you execute `python dashboard.py` directly.
if __name__ == '__main__':
    # This starts the web server. `debug=False` is important for production/deployment.
    app.run_server(debug=False)

