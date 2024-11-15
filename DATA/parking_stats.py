import json
from influxdb import InfluxDBClient
import numpy as np
import pandas as pd
import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

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
            print(df)
            return df
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching data: {e}")
            return pd.DataFrame()


    def plot_occupancy(self, df):
        if not df.empty:
            total_sensors = df['ID'].nunique()
            df_occupied = df[df['status'] == 'occupied']
            df_occupied['time'] = df_occupied['time'].dt.floor('T')
            df_minute_counts = df_occupied.groupby('time').size().reset_index(name='occupied_count')
            df_minute_counts['hour'] = df_minute_counts['time'].dt.floor('H')
            df_hourly_avg = df_minute_counts.groupby('hour')['occupied_count'].mean().reset_index()
            
            df_hourly_avg['occupancy_percentage'] = (df_hourly_avg['occupied_count'] / total_sensors) * 100

            df_hourly_avg['occupied_count'] = df_hourly_avg['occupied_count'].apply(
            lambda x: np.ceil(x) if x - int(x) >= 0.5 else np.floor(x)
        )

            fig = go.Figure(data=[
                go.Scatter(
                    x=df_hourly_avg['hour'],
                    y=df_hourly_avg['occupied_count'],  # Average occupancy count per hour
                    mode='lines+markers',
                    name="Average Hourly Parking Occupancy",
                    line=dict(color='royalblue', width=2)
                )
            ])

            fig.update_layout(
                title="Average Hourly Parking Occupancy",
                xaxis_title="Time",
                yaxis_title="Average Occupied Parkings",
                showlegend=False
            )
            
            fig2 = go.Figure(data=[
            go.Scatter(
                x=df_hourly_avg['hour'],
                y=df_hourly_avg['occupancy_percentage'],
                mode='lines+markers',
                name="Percentage Hourly Parking Occupancy",
                line=dict(color='green', width=2))
            ])
        

            fig2.update_layout(
            title="Hourly Percentage of Parking Occupancy",
            xaxis_title="Time",
            yaxis_title="Percentage of Occupied Parkings",
            showlegend=False)   
            st.plotly_chart(fig)
            st.plotly_chart(fig2)
        else:
            st.write("No data to display for occupancy.")

    def run(self, parking_id):
        st.title("Parking Hourly Occupancy Dashboard")
        st.write("Visualize the occupancy of parking spots over time")
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

            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
            df.drop(columns=['booking_code'], inplace=True)
            print(df)
            return df
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching fee data: {e}")
            return pd.DataFrame()

    def plot_fees(self, df):
        if not df.empty:
   
            df['time'] = df['time'].dt.floor('H')
        
 
            df_hourly = df.groupby('time')['fee'].sum().reset_index()
            df_hourly = df_hourly.set_index('time').resample('H').sum().reset_index()

            fig = go.Figure(data=[
            go.Bar(
                x=df_hourly['time'],
                y=df_hourly['fee'],  
                name="Total Fees",
                text=df_hourly['fee'].apply(lambda x: f"€{x:.2f}"),  # Show as currency
                textposition='auto')
            ])
        
            fig.update_layout(
            title="Total Fees Collected",
            xaxis_title="Time",
            yaxis_title="Total Hourly Fees (Euro)",
            showlegend=False)
        
            st.plotly_chart(fig)
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
            df.drop(columns=['booking_code'], inplace=True)
            print(df)
            return df
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching duration data: {e}")
            return pd.DataFrame()
    def plot_durations(self, df):
        if not df.empty:
            df['total_seconds'] = df['duration'] * 3600 
            df['minutes'] = (df['total_seconds'] // 60).astype(int) 
            df['seconds'] = (df['total_seconds'] % 60).astype(int)  
        

            df['duration_formatted'] = df['minutes'].astype(str) + ' min ' + df['seconds'].astype(str) + ' sec'
        
            fig = go.Figure(data=[
                go.Bar(
                x=df['time'], 
                y=df['total_seconds'] / 60, 
                text=df['duration_formatted'],  
                textposition='auto',  
                name="Duration")
            ])
        
        # Customize layout
            fig.update_layout(
                title="Parking Duration Over Time",
                xaxis_title="Time",
                yaxis_title="Duration of parkings(Minutes)",
                yaxis_tickformat=",", 
                showlegend=False)
        
            st.plotly_chart(fig)
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


