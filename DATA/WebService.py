import pandas as pd
import streamlit as st
import requests


def fetch_sensors():
    # Get sensor data by contacting the adaptor (you may need to adapt the URL)
    try:    
        response = requests.get("http://localhost:5001/")
        response.raise_for_status()
        data = response.json()
        #st.write(data)
        df = pd.DataFrame(data)
        #st.write(df)
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
        df.drop(columns=['booking_code'], inplace=True)
        return df
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

def toggle_sensor(sensor_id, new_state):
    # Send POST request to device connector
    data = {"sensor_id": sensor_id, "state": new_state}
    response = requests.post("http://localhost:8083/changeState", json=data)
    return response.ok

sensors = fetch_sensors()
if 'state' not in sensors.columns:
    sensors['state'] = 'active'
#print(sensors)

if 'sensor_states' not in st.session_state:
    st.session_state.sensor_states = {row['ID']: row['state'] for _, row in sensors.iterrows()}

# Display the sensors data as a table with an extra "Action" column
st.write("Current Sensors List:")

# Iterate over each row to add an activate/deactivate button
for idx, row in sensors.iterrows():
    col1, col2 = st.columns([4, 1])  # Create columns for data and button
    
    with col1:
        st.write(row.drop(['state']).to_frame().T)  # Show row data without 'state' column
        
    with col2:
        # Use session state to get the current state of the sensor
        current_state = st.session_state.sensor_states[row['ID']]
        new_state = "active" if current_state == "inactive" else "inactive"
        button_label = "Activate" if new_state == "active" else "Deactivate"

        # Show the button for activating/deactivating
        if st.button(button_label, key=row['ID']):
            # Toggle the state
            success = toggle_sensor(row['ID'], new_state)
            if success:
                # Update the session state for the sensor
                st.session_state.sensor_states[row['ID']] = new_state
                st.success(f"Sensor {row['ID']} set to {new_state}")
            else:
                st.error("Failed to update sensor state")
else:
    st.write("No sensor data available.")

    # Display the sensors data as a table with an extra "Action" column
# st.write("Current Sensors List:")
   
# # Iterate over each row to add an activate/deactivate button
# for idx, row in sensors.iterrows():
    
#     col1, col2 = st.columns([4, 1])  # Adjust column sizes as needed
    
#     with col1:
#         # Show the row data without 'state' column for cleaner output
#         st.write(row.drop(['state']).to_frame().T)  # Display row data

        
#     with col2:
#         # Determine current state and button label
#         current_state = row['state']
#         new_state = "active" if current_state == "inactive" else "inactive"
#         button_label = "Activate" if new_state == "active" else "Deactivate"

#         # Show the button for activating/deactivating
#         if st.button(button_label, key=row['ID']):
#             # Toggle the state
#             success = toggle_sensor(row['ID'], new_state)
#             if success:
#                 # Update the state in the DataFrame
#                 sensors.at[idx, 'state'] = new_state  # Change the state for the button label to reflect
#                 st.success(f"Sensor {row['ID']} set to {new_state}")
#             else:
#                 st.error("Failed to update sensor state")

