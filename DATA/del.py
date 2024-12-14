from influxdb import InfluxDBClient
from pathlib import Path
import json
P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

def delete_all_sensors():
    try:
        # Connection to influxDB
        settings = json.load(open(SETTINGS))
        influx_port = settings["influxPort"]
        client = InfluxDBClient(host='localhost', port=influx_port, username='root', password='root', database='IoT_Smart_Parking')

        # Query to cancel all status points
        delete_query = 'DELETE FROM "status"'
        client.query(delete_query)
        
        print("All sensor have been deleted from database.")
    
    except Exception as e:
        print(f"Error during sensor deletion: {e}")

# Execute the function to remove all points from influx
delete_all_sensors()
