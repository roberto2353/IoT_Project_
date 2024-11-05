from influxdb import InfluxDBClient
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt


import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone

# Define the adaptor's URL
ADAPTOR_URL = "http://localhost:5001/sensors/occupied"  # Adjust if the adaptor runs on a different URL or port

# Function to fetch data from the adaptor within a specified time range
def fetch_data(start=None, end=None):
    # Prepare the parameters
    params = {}
    if start:
        params['start'] = start
    if end:
        params['end'] = end

    try:
        # Make a GET request to the adaptor
        response = requests.get(ADAPTOR_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Convert the data to a DataFrame
        df = pd.DataFrame(data)
        
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

# Streamlit app title and description
st.title("Parking Statistics Dashboard")
st.write("Visualize the occupancy count of parking sensors over time")

# Dropdown for time range selection
time_range = st.selectbox("Select Time Range", ["Last Day", "Last Week", "Last Month"])

# Calculate the start and end time based on the selected range
end_time = datetime.now(timezone.utc)  # End time is now in UTC (ISO format for InfluxDB)
if time_range == "Last Day":
    start_time = (datetime.now(timezone.utc) - timedelta(days=1))
elif time_range == "Last Week":
    start_time = (datetime.now(timezone.utc) - timedelta(weeks=1)) 
elif time_range == "Last Month":
    start_time = (datetime.now(timezone.utc) - timedelta(weeks=4))

start_time = int(start_time.timestamp() * 1000000000) #nanoseconds
end_time = int(end_time.timestamp() * 1000000000)
# Fetch data from the adaptor
df_filtered = fetch_data(start=start_time, end=end_time)

# Filter for 'occupied' status
#df_filtered = df[df['status'] == 'occupied']

# Group by hour and count the number of occupied sensors
df_filtered['time'] = df_filtered['time'].dt.floor('H')  # Round down to the nearest hour
df_grouped = df_filtered.groupby('time').size().reset_index(name='occupied_count')

# Plot the results
st.line_chart(df_grouped.set_index('time')['occupied_count'])
st.write("Occupancy count by hour")


