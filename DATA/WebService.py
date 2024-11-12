import pandas as pd
import streamlit as st
import requests
import json
from pathlib import Path
P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class SensorDashboard:
    def __init__(self, catalog_url, adaptor_url):
        self.catalog_url = catalog_url
        self.adaptor_url = adaptor_url
        self.devConn_url = ""

    def fetch_parkings(self):
        # Get available parkings from the catalog
        try:
            response = requests.get(f"{self.catalog_url}/parkings")
            response.raise_for_status()
            data = response.json()
            #parkings = {parking['ID']: parking['name'] for parking in data['parkings']}
            #self.devConn_url = f'http://{data["parkings"]["url"]}:{data["parkings"]["port"]}'
            return data
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching parkings: {e}")
            return {}

    def fetch_sensors(self, parking_name):
        # Fetch sensors for the selected parking
        try:
            
            response = requests.get(self.adaptor_url)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data)
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
            df.drop(columns=['booking_code'], inplace=True)
            df = df[df['parking_id'] == parking_name]
            return df
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching sensors: {e}")
            return pd.DataFrame()

    def toggle_sensor(self, sensor_id, new_state):
        # Toggle sensor state by sending POST request to the device connector
        data = {"sensor_id": sensor_id, "state": new_state}
        response = requests.post(f"{self.devConn_url}/changeState", json=data)
        return response.ok

    def display_sensors(self, sensors):
        # Initialize session state for sensor states if not already done
        if 'sensor_states' not in st.session_state:
            st.session_state.sensor_states = {row['ID']: row['active'] for _, row in sensors.iterrows()}

        # Display the sensors data as a table with an extra "Action" column
        st.write("Current Sensors List:")
        for idx, row in sensors.iterrows():
            col1, col2 = st.columns([4, 1])  # Create columns for data and button
            
            with col1:
                st.write(row.drop(['active']).to_frame().T)  # Show row data without 'state' column
            
            with col2:
                current_state = st.session_state.sensor_states[row['ID']]
                new_state = "active" if current_state == "inactive" else "inactive"
                button_label = "Activate" if new_state == "active" else "Deactivate"

                # Show the button for activating/deactivating
                if st.button(button_label, key=row['ID']):
                    success = self.toggle_sensor(row['ID'], new_state)
                    if success:
                        st.session_state.sensor_states[row['ID']] = new_state
                        st.success(f"Sensor {row['ID']} set to {new_state}")
                    else:
                        st.error("Failed to update sensor state")

    def run(self):
        st.title("Parking Sensor Dashboard")
        
        # Step 1: Select parking from catalog
        data = self.fetch_parkings()
        if data:
            parkings = {parking['ID']: parking['name'] for parking in data['parkings']}
            parking_name = st.sidebar.selectbox("Select Parking", list(parkings.values()))
            st.write(f"Selected Parking: {parking_name}")
            selected_parking = next(parking for parking in data['parkings'] if parking['name'] == parking_name)
            self.devConn_url = f"http://{selected_parking['url']}:{selected_parking['port']}"
            # Step 2: Fetch and display sensors for selected parking
            sensors = self.fetch_sensors(parking_name)
            if not sensors.empty:
                self.display_sensors(sensors)
            else:
                st.write("No sensor data available for the selected parking.")
        else:
            st.write("No parkings available.")

def main():
    settings = json.load(open(SETTINGS))
    adaptor_port = settings['serviceInfo']['port'] 
    catalog_url = settings['catalog_url']
    adaptor_url = f"http://localhost:{adaptor_port}"  # Replace with the actual adaptor URL

    dashboard = SensorDashboard(catalog_url, adaptor_url)
    dashboard.run()

if __name__ == "__main__":
    main()


# import pandas as pd
# import streamlit as st
# import requests


# def fetch_sensors():
#     # Get sensor data by contacting the adaptor (you may need to adapt the URL)
#     try:    
#         #user can choose the parking -> ask catalog, get names and then add a query in adaptor that specifies
#         #the parking (add in the database the parking name for each sensor)
#         response = requests.get("http://localhost:5001/")
#         response.raise_for_status()
#         data = response.json()
#         #st.write(data)
#         df = pd.DataFrame(data)
#         #st.write(df)
#         if 'time' in df.columns:
#             df['time'] = pd.to_datetime(df['time'])
#         df.drop(columns=['booking_code'], inplace=True)
#         return df
    
#     except requests.exceptions.RequestException as e:
#         st.error(f"Error fetching data: {e}")
#         return pd.DataFrame()  # Return an empty DataFrame on error

# def toggle_sensor(sensor_id, new_state):
#     # Send POST request to device connector
#     data = {"sensor_id": sensor_id, "state": new_state}
#     response = requests.post("http://localhost:8083/changeState", json=data)
#     return response.ok

# sensors = fetch_sensors()
# if 'state' not in sensors.columns:
#     sensors['state'] = 'active'
# #print(sensors)

# if 'sensor_states' not in st.session_state:
#     st.session_state.sensor_states = {row['ID']: row['state'] for _, row in sensors.iterrows()}

# # Display the sensors data as a table with an extra "Action" column
# st.write("Current Sensors List:")

# # Iterate over each row to add an activate/deactivate button
# for idx, row in sensors.iterrows():
#     col1, col2 = st.columns([4, 1])  # Create columns for data and button
    
#     with col1:
#         st.write(row.drop(['state']).to_frame().T)  # Show row data without 'state' column
        
#     with col2:
#         # Use session state to get the current state of the sensor
#         current_state = st.session_state.sensor_states[row['ID']]
#         new_state = "active" if current_state == "inactive" else "inactive"
#         button_label = "Activate" if new_state == "active" else "Deactivate"

#         # Show the button for activating/deactivating
#         if st.button(button_label, key=row['ID']):
#             # Toggle the state
#             success = toggle_sensor(row['ID'], new_state)
#             if success:
#                 # Update the session state for the sensor
#                 st.session_state.sensor_states[row['ID']] = new_state
#                 st.success(f"Sensor {row['ID']} set to {new_state}")
#             else:
#                 st.error("Failed to update sensor state")
# else:
#     st.write("No sensor data available.")

 