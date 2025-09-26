import requests
import pandas as pd

APP_INSIGHTS_APP_ID = ""
API_KEY = ""

def build_kql_queries(start_timestamp, end_timestamp):
    """
    Returns KQL queries for traces, dependencies, and exceptions for the given time range.
    """
    traces_query = f"""
        let startTime = datetime({start_timestamp});
        let endTime = datetime({end_timestamp});

        traces
        | where timestamp between (startTime .. endTime)
    """
    dependencies_query = f"""
        let startTime = datetime({start_timestamp});
        let endTime = datetime({end_timestamp});

        dependencies
        | where timestamp between (startTime .. endTime)
    """
    exceptions_query = f"""
        let startTime = datetime({start_timestamp});
        let endTime = datetime({end_timestamp});

        exceptions
        | where timestamp between (startTime .. endTime)
    """
    return traces_query, dependencies_query, exceptions_query

def run_kql_query(app_id: str, api_key: str, kql_query: str) -> pd.DataFrame:
    """
    Executes a KQL query on Azure Application Insights and returns the result as a DataFrame.
    Automatically flattens 'customDimensions' if present.

    Parameters:
        app_id (str): The Application Insights App ID.
        api_key (str): The API key with read permissions.
        kql_query (str): The KQL query string.

    Returns:
        pd.DataFrame: Resulting DataFrame, with flattened 'customDimensions' if applicable.
    """
    endpoint = f"https://api.applicationinsights.io/v1/apps/{app_id}/query"
    headers = {
        "x-api-key": api_key
    }
    params = {
        "query": kql_query
    }

    response = requests.get(endpoint, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        rows = data['tables'][0]['rows']
        columns = data['tables'][0]['columns']
        column_names = [col['name'] for col in columns]

        df = pd.DataFrame(rows, columns=column_names)

        return df

    else:
        raise Exception(f"Query failed: {response.status_code} {response.text}")
    
def get_oldest_exception_with_dependency(
    exceptions_df, dependencies_df, start_time, end_time
    ):
    # Convert timestamp columns
    exceptions_df['timestamp'] = pd.to_datetime(exceptions_df['timestamp'])
    dependencies_df['timestamp'] = pd.to_datetime(dependencies_df['timestamp'])

    # Filter exceptions within the given time range
    filtered_exceptions = exceptions_df[
        (exceptions_df['timestamp'] >= start_time) &
        (exceptions_df['timestamp'] <= end_time)
    ]

    if filtered_exceptions.empty:
        return pd.DataFrame()  # No records in range

    # Find the oldest exception
    oldest_exception = filtered_exceptions.sort_values('timestamp').iloc[0:1]

    # Perform the join
    joined_df = pd.merge(
        oldest_exception,
        dependencies_df,
        how='left',
        left_on='operation_ParentId',
        right_on='id',
        #suffixes=('_exception_table', '_dependency_table')
    )

    return joined_df

# def get_last_child_info(start_id, df):
#     current_id = start_id
#     visited = set()

#     # For faster lookups
#     df_indexed = df.set_index("id")

#     last_inproc_row = None  # To store the last 'InProc' child found

#     while True:
#         if current_id in visited:
#             # Prevent infinite loops in case of circular references
#             break
#         visited.add(current_id)

#         if current_id not in df_indexed.index:
#             break

#         row = df_indexed.loc[current_id]

#         # Check if this row is type == 'InProc'
#         if row["type"] == "InProc":
#             last_inproc_row = row

#         # Find child row where operation_ParentId == current_id
#         children = df[df["operation_ParentId"] == current_id]

#         if children.empty:
#             # No further child → end
#             break

#         # Pick the first child (can modify if you have other rules)
#         current_id = children.iloc[0]["id"]

#     if last_inproc_row is not None:
#         return last_inproc_row[["target", "type"]]

#     return None

def get_last_child_info_until_http_or_blob(start_id, df):
    current_id = start_id
    visited = set()
    df_indexed = df.set_index("id")
    last_inproc_row = None

    while True:
        if current_id in visited:
            break  # Prevent circular loops
        visited.add(current_id)

        if current_id not in df_indexed.index:
            break

        row = df_indexed.loc[current_id]

        # Stop if type is "HTTP" or "Azure blob"
        if row["type"].lower() in ("https", "azure blob"):
            break

        if row["type"].lower() == "inproc":
            last_inproc_row = row

        # Move to first child
        children = df[df["operation_ParentId"] == current_id]
        if children.empty:
            break

        current_id = children.iloc[0]["id"]

    return last_inproc_row[["target", "type"]] if last_inproc_row is not None else None


def get_concatenated_messages(parent_id, traces_df, sep=" | \n "):
    # Filter matching rows
    matches = traces_df[traces_df["operation_ParentId"] == parent_id]

    if matches.empty:
        return None

    # Drop NaN messages, convert to string, and join
    concatenated = sep.join(matches["message"].dropna().astype(str))
    return concatenated

def get_final_df(output_df, columns_to_display, concatenated_message):
    # Filter columns
    final_df = output_df[columns_to_display].copy()

    # Apply the get_concatenated_messages function
    final_df["request_response_message"] = concatenated_message

    return final_df

def get_logs_for_time_range(start_timestamp, end_timestamp):

    traces_query, dependencies_query, exceptions_query = build_kql_queries(start_timestamp, end_timestamp)
    # Run KQL queries
    traces_df = run_kql_query(APP_INSIGHTS_APP_ID, API_KEY, traces_query)
    dependencies_df = run_kql_query(APP_INSIGHTS_APP_ID, API_KEY, dependencies_query)
    exceptions_df = run_kql_query(APP_INSIGHTS_APP_ID, API_KEY, exceptions_query)

    # Get oldest exception with dependency
    output_df = get_oldest_exception_with_dependency(
        exceptions_df, dependencies_df, pd.Timestamp(start_timestamp), pd.Timestamp(end_timestamp)
    )

    # Get last child info
    if not output_df.empty:
        parent_id = output_df["operation_ParentId_x"].iloc[0]
        last_child_info = get_last_child_info_until_http_or_blob(parent_id, dependencies_df)
        if last_child_info is not None:
            trace_parent_id = last_child_info.name
        else:
            trace_parent_id = parent_id
        # print(last_child_info.name)
        messages = get_concatenated_messages(trace_parent_id, traces_df, sep=" \n ")
        # print(messages)
    else:
        messages = None

    # Columns to display (reuse your list)
    columns_to_display = [
        'timestamp_x', 'type_x', 'outerMessage', 'details', 'customDimensions_x',
        'operation_Id_x', 'operation_ParentId_x', 'client_Type_x', 'client_OS_x',
        'client_City_x', 'client_StateOrProvince_x', 'client_CountryOrRegion_x',
        'cloud_RoleInstance_x', 'id', 'target', 'type_y', 'duration',
        'performanceBucket', 'operation_ParentId_y'
    ]

    # Build final_df
    final_df = get_final_df(output_df, columns_to_display, messages)

    final_df = final_df.rename(columns={
        "timestamp_x": "timestamp",
        "type_x": "exception_type",
        "outerMessage": "exception_message",
        "details": "exception_details",
        "customDimensions_x": "exception_customDimensions",
        "operation_Id_x": "exception_operation_Id",
        "operation_ParentId_x": "exception_operation_ParentId",
        "client_Type_x": "client_Type",
        "client_OS_x": "client_OS",
        "client_City_x": "client_City",
        "client_StateOrProvince_x": "client_StateOrProvince",
        "client_CountryOrRegion_x": "client_CountryOrRegion",
        "cloud_RoleInstance_x": "cloud_RoleInstance",
        "id": "dependency_id",
        "target": "target_function",
        "type_y": "dependency_type",
        "operation_ParentId_y": "dependency_operation_ParentId",
    })
    return final_df

# Example usage:
# df1 = get_logs_for_time_range('2025-08-11T12:03:00Z', '2025-08-11T12:04:00Z')
# print(df1)