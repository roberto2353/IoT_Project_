from influxdb import InfluxDBClient
import pandas as pd
import streamlit as st
import requests
from datetime import datetime, timedelta, timezone

class BaseDashboard:
    @staticmethod
    def select_time_range():
        """
        Allow the user to select a time range and return the corresponding timestamps.
        """
        time_range = st.selectbox("Select Time Range", ["Last Day", "Last Week", "Last Month"])
        end_time = datetime.now(timezone.utc)
        if time_range == "Last Day":
            start_time = end_time - timedelta(days=1)
        elif time_range == "Last Week":
            start_time = end_time - timedelta(weeks=1)
        elif time_range == "Last Month":
            start_time = end_time - timedelta(weeks=4)

        return int(start_time.timestamp() * 1e9), int(end_time.timestamp() * 1e9)

class ParkingDashboard(BaseDashboard):
    def __init__(self, adaptor_url):
        self.adaptor_url = adaptor_url

    def fetch_data(self, start=None, end=None):
        params = {'start': start, 'end': end}
        try:
            response = requests.get(self.adaptor_url, params=params)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data)
            
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
            return df
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching data: {e}")
            return pd.DataFrame()

    def plot_occupancy(self, df):
        if not df.empty:
            df['time'] = df['time'].dt.floor('H')
            df_grouped = df.groupby('time').size().reset_index(name='occupied_count')
            st.line_chart(df_grouped.set_index('time')['occupied_count'])
            st.write("Occupancy count by hour")
        else:
            st.write("No data to display for this time range.")

    def run(self):
        st.title("Parking Occupancy Dashboard")
        st.write("Visualize the occupancy count of parking sensors over time")
        start_time, end_time = self.select_time_range()
        df_filtered = self.fetch_data(start=start_time, end=end_time)
        self.plot_occupancy(df_filtered)

class FeeDashboard(BaseDashboard):
    def __init__(self, fee_adaptor_url):
        self.fee_adaptor_url = fee_adaptor_url

    def fetch_fees(self, start=None, end=None):
        params = {'start': start, 'end': end}
        try:
            response = requests.get(self.fee_adaptor_url, params=params)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data)
            #print(df)
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
            return df
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching fee data: {e}")
            return pd.DataFrame()

    def plot_fees(self, df):
        if not df.empty:
            df.rename(columns={'fee': 'Fee (Euro)'}, inplace=True)
            st.bar_chart(df.set_index('time')['Fee (Euro)'])
            st.write("Fees collected over time")
        else:
            st.write("No data to display for fees.")

    def run(self):
        st.title("Parking Fees Dashboard")
        st.write("Visualize the parking fees collected over time")
        start_time, end_time = self.select_time_range()
        df_fees = self.fetch_fees(start=start_time, end=end_time)
        self.plot_fees(df_fees)

class DurationDashboard(BaseDashboard):
    def __init__(self, duration_adaptor_url):
        self.duration_adaptor_url = duration_adaptor_url

    def fetch_durations(self, start=None, end=None):
        params = {'start': start, 'end': end}
        try:
            response = requests.get(self.duration_adaptor_url, params=params)
            response.raise_for_status()
            data = response.json()
            print(data)
            print("paperino")
            df = pd.DataFrame(data)
            print("pippo")
            print(df)
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
            return df
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching duration data: {e}")
            return pd.DataFrame()

    def plot_durations(self, df):
        if not df.empty:
            st.line_chart(df.set_index('time')['duration'])
            st.write("Parking durations over time")
        else:
            st.write("No data to display for durations.")

    def run(self):
        st.title("Parking Duration Dashboard")
        st.write("Visualize the duration of parking over time")
        start_time, end_time = self.select_time_range()
        df_durations = self.fetch_durations(start=start_time, end=end_time)
        self.plot_durations(df_durations)

# Streamlit app with sidebar to navigate between dashboards
def main():
    st.sidebar.title("Navigation")
    dashboard_choice = st.sidebar.selectbox("Choose Dashboard", ["Occupancy", "Fees", "Durations"])

    # URLs for each data source (replace with actual URLs if different)
    OCCUPANCY_URL = "http://localhost:5001/sensors/occupied"
    FEE_URL = "http://localhost:5001/fees"
    DURATION_URL = "http://localhost:5001/durations"

    if dashboard_choice == "Occupancy":
        dashboard = ParkingDashboard(adaptor_url=OCCUPANCY_URL)
    elif dashboard_choice == "Fees":
        dashboard = FeeDashboard(fee_adaptor_url=FEE_URL)
    elif dashboard_choice == "Durations":
        dashboard = DurationDashboard(duration_adaptor_url=DURATION_URL)

    dashboard.run()

if __name__ == "__main__":
    main()






# from influxdb import InfluxDBClient
# import pandas as pd
# import streamlit as st
# import matplotlib.pyplot as plt


# import requests
# import pandas as pd
# import streamlit as st
# import matplotlib.pyplot as plt
# from datetime import datetime, timedelta, timezone

# from influxdb import InfluxDBClient
# import pandas as pd
# import streamlit as st
# import matplotlib.pyplot as plt
# from datetime import datetime, timedelta, timezone
# import requests

# class ParkingDashboard:
#     def __init__(self, adaptor_url):
#         self.adaptor_url = adaptor_url

#     def fetch_data(self, start=None, end=None):
#         """
#         Fetch data from the adaptor within a specified time range.
#         """
#         params = {}
#         if start:
#             params['start'] = start
#         if end:
#             params['end'] = end

#         try:
#             response = requests.get(self.adaptor_url, params=params)
#             response.raise_for_status()
#             data = response.json()
#             df = pd.DataFrame(data)
            
#             if 'time' in df.columns:
#                 df['time'] = pd.to_datetime(df['time'])
#             return df
#         except requests.exceptions.RequestException as e:
#             st.error(f"Error fetching data: {e}")
#             return pd.DataFrame()

#     def plot_occupancy(self, df):
#         """
#         Plot occupancy data by hour.
#         """
#         if not df.empty:
#             df['time'] = df['time'].dt.floor('H')
#             df_grouped = df.groupby('time').size().reset_index(name='occupied_count')
#             st.line_chart(df_grouped.set_index('time')['occupied_count'])
#             st.write("Occupancy count by hour")
#         else:
#             st.write("No data to display for this time range.")

#     def select_time_range(self):
#         """
#         Allow the user to select a time range and return the corresponding timestamps.
#         """
#         time_range = st.selectbox("Select Time Range", ["Last Day", "Last Week", "Last Month"])
#         end_time = datetime.now(timezone.utc)
#         if time_range == "Last Day":
#             start_time = end_time - timedelta(days=1)
#         elif time_range == "Last Week":
#             start_time = end_time - timedelta(weeks=1)
#         elif time_range == "Last Month":
#             start_time = end_time - timedelta(weeks=4)

#         return int(start_time.timestamp() * 1e9), int(end_time.timestamp() * 1e9)

#     def run(self):
#         """
#         Main function to run the dashboard.
#         """
#         st.title("Parking Statistics Dashboard")
#         st.write("Visualize the occupancy count of parking sensors over time")

#         # Get time range
#         start_time, end_time = self.select_time_range()

#         # Fetch and display data
#         df_filtered = self.fetch_data(start=start_time, end=end_time)
#         self.plot_occupancy(df_filtered)


# # Instantiate and run the dashboard
# dashboard = ParkingDashboard(adaptor_url="http://localhost:5001/sensors/occupied")
# dashboard.run()



# Define the adaptor's URL
# ADAPTOR_URL = "http://localhost:5001/sensors/occupied"  # Adjust if the adaptor runs on a different URL or port

# # Function to fetch data from the adaptor within a specified time range
# def fetch_data(start=None, end=None):
#     # Prepare the parameters
#     params = {}
#     if start:
#         params['start'] = start
#     if end:
#         params['end'] = end

#     try:
#         # Make a GET request to the adaptor
#         response = requests.get(ADAPTOR_URL, params=params)
#         response.raise_for_status()
#         data = response.json()
        
#         # Convert the data to a DataFrame
#         df = pd.DataFrame(data)
        
#         if 'time' in df.columns:
#             df['time'] = pd.to_datetime(df['time'])
#         return df
#     except requests.exceptions.RequestException as e:
#         st.error(f"Error fetching data: {e}")
#         return pd.DataFrame()  # Return an empty DataFrame on error

# # Streamlit app title and description
# st.title("Parking Statistics Dashboard")
# st.write("Visualize the occupancy count of parking sensors over time")

# # Dropdown for time range selection
# time_range = st.selectbox("Select Time Range", ["Last Day", "Last Week", "Last Month"])

# # Calculate the start and end time based on the selected range
# end_time = datetime.now(timezone.utc)  # End time is now in UTC (ISO format for InfluxDB)
# if time_range == "Last Day":
#     start_time = (datetime.now(timezone.utc) - timedelta(days=1))
# elif time_range == "Last Week":
#     start_time = (datetime.now(timezone.utc) - timedelta(weeks=1)) 
# elif time_range == "Last Month":
#     start_time = (datetime.now(timezone.utc) - timedelta(weeks=4))

# start_time = int(start_time.timestamp() * 1000000000) #nanoseconds
# end_time = int(end_time.timestamp() * 1000000000)
# # Fetch data from the adaptor
# df_filtered = fetch_data(start=start_time, end=end_time)

# # Filter for 'occupied' status
# #df_filtered = df[df['status'] == 'occupied']

# # Group by hour and count the number of occupied sensors
# df_filtered['time'] = df_filtered['time'].dt.floor('H')  # Round down to the nearest hour
# df_grouped = df_filtered.groupby('time').size().reset_index(name='occupied_count')

# # Plot the results
# st.line_chart(df_grouped.set_index('time')['occupied_count'])
# st.write("Occupancy count by hour")


