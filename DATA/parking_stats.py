import json
from influxdb import InfluxDBClient
import pandas as pd
import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

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

    def fetch_data(self, start=None, end=None, parking_id=None):
        params = {'start': start, 'end': end, 'parking_id': parking_id}
        try:
            response = requests.get(self.adaptor_url, params=params)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data)            
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
            #print("occupied", df)
            return df
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching data: {e}")
            return pd.DataFrame()

    def plot_occupancy(self, df):
        if not df.empty:
            
        
        # Ensure 'time' is in hourly resolution
            df['time'] = df['time'].dt.floor('T')
            print(df)
        # Group by the time column and count occurrences
            df_grouped = df.groupby('time').size().reset_index(name='occupied_count')
            print(df_grouped)
        # Plot if there is data
            if not df_grouped.empty:
                st.line_chart(df_grouped.set_index('time')['occupied_count'])
                st.write("Occupancy count by hour")
            else:
                st.write("No data to display for this time range.")
        else:
            st.write("No data to display for this time range.")

    def run(self, parking_id):
        st.title("Parking Occupancy Dashboard")
        st.write("Visualize the occupancy count of parking sensors over time")
        start_time, end_time = self.select_time_range()
        df_filtered = self.fetch_data(start=start_time, end=end_time, parking_id=parking_id)
        self.plot_occupancy(df_filtered)

class FeeDashboard(BaseDashboard):
    def __init__(self, fee_adaptor_url):
        self.fee_adaptor_url = fee_adaptor_url

    def fetch_fees(self, start=None, end=None, parking_id=None):
        params = {'start': start, 'end': end, 'parking_id': parking_id}
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

    def run(self, parking_id):
        st.title("Parking Fees Dashboard")
        st.write("Visualize the parking fees collected over time")
        start_time, end_time = self.select_time_range()
        df_fees = self.fetch_fees(start=start_time, end=end_time, parking_id=parking_id)
        self.plot_fees(df_fees)

class DurationDashboard(BaseDashboard):
    def __init__(self, duration_adaptor_url):
        self.duration_adaptor_url = duration_adaptor_url

    def fetch_durations(self, start=None, end=None, parking_id=None):
        params = {'start': start, 'end': end, 'parking_id': parking_id}
        try:
            response = requests.get(self.duration_adaptor_url, params=params)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data)
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
            return df
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching duration data: {e}")
            return pd.DataFrame()

    def plot_durations(self, df):
        if not df.empty:
            df['duration_minutes'] = df['duration'] * 60  # Convert hours to minutes
            #df['durations'] = df['duration_minutes'].apply(
            #    lambda x: f"{int(x)}m {int((x - int(x)) * 60)}s"
            #)  # Format as minutes and seconds
            
            # Plot using minutes as the y-axis value
            st.bar_chart(df.set_index('time')['duration_minutes'])
            
            
            # Optionally, display the exact formatted durations in a table
            #st.write("Exact durations:")
            #st.write(df[['time', 'durations']])
        else:
            st.write("No data to display for durations.")

    def run(self, parking_id):
        st.title("Parking Duration Dashboard")
        st.write("Visualize the duration of parking over time")
        start_time, end_time = self.select_time_range()
        df_durations = self.fetch_durations(start=start_time, end=end_time, parking_id=parking_id)
        self.plot_durations(df_durations)
    
class ParkingSelector:
    def __init__(self, catalog_url):
        self.catalog_url = catalog_url

    def fetch_parkings(self):
        try:
            response = requests.get(f"{self.catalog_url}/parkings")
            response.raise_for_status()
            parkings = response.json()
            #(parkings)
            return parkings
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching parkings: {e}")
            return []

    def select_parking(self, parkings):
        if parkings:
            #print(parkings)
            parking_choices = {parking['name']: parking['ID'] for parking in parkings}
            # Display the names in the dropdown
            selected_parking_name = st.sidebar.selectbox("Select Parking", list(parking_choices.keys()))
            return selected_parking_name
        return print("No parkings in the catalog!")

# Streamlit app with sidebar to navigate between dashboards
def main():
    settings = json.load(open(SETTINGS))
    adaptor_port = settings['serviceInfo']['port'] 
    catalog_url = settings['catalog_url']

    parking_selector = ParkingSelector(catalog_url)
    available_parkings = parking_selector.fetch_parkings()
    selected_parking_id = parking_selector.select_parking(available_parkings['parkings'])
    st.sidebar.title("Navigation")
    dashboard_choice = st.sidebar.selectbox("Choose Dashboard", ["Occupancy", "Fees", "Durations"])

    # URLs for each data source (replace with actual URLs if different)
    OCCUPANCY_URL = f"http://localhost:{adaptor_port}/sensors/occupied"
    FEE_URL = f"http://localhost:{adaptor_port}/fees"
    DURATION_URL = f"http://localhost:{adaptor_port}/durations"

    if dashboard_choice == "Occupancy":
        dashboard = ParkingDashboard(adaptor_url=OCCUPANCY_URL)
    elif dashboard_choice == "Fees":
        dashboard = FeeDashboard(fee_adaptor_url=FEE_URL)
    elif dashboard_choice == "Durations":
        dashboard = DurationDashboard(duration_adaptor_url=DURATION_URL)

    if dashboard_choice == "Occupancy":
        dashboard = ParkingDashboard(adaptor_url=OCCUPANCY_URL)
    elif dashboard_choice == "Fees":
        dashboard = FeeDashboard(fee_adaptor_url=FEE_URL)
    elif dashboard_choice == "Durations":
        dashboard = DurationDashboard(duration_adaptor_url=DURATION_URL)

    if selected_parking_id:
        dashboard.run(parking_id=selected_parking_id)

if __name__ == "__main__":
    main()


