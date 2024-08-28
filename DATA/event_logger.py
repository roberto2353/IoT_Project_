from datetime import datetime  # Modifica questa riga
from influxdb_client import InfluxDBClient, Point, WritePrecision,WriteOptions
from pathlib import Path
import json

class EventLogger:
    def __init__(self):
        # Configura la connessione a InfluxDB
        self.url = "http://localhost:8086"  # URL del tuo server InfluxDB
        self.token = "jChkOn7dUi9p93q-0OnquPcZYNHEgrimJ1XwogkODbx7GTWTKA8RzArEVwa5vMs01aRZO0XABIJRwlms8fBeHA=="  # Token di autenticazione
        self.org = "Group8"  # Organizzazione
        self.bucket = "Parking_events"  # Bucket per memorizzare i dati
        
        # Crea il client InfluxDB
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=WriteOptions())
        
    def log_event(self, slot_id, previous_status, current_status, duration):
        """Logga un evento in InfluxDB."""
        print(f"Logging event to InfluxDB: Slot ID={slot_id}, Previous Status={previous_status}, Current Status={current_status}, Duration={duration}")
        
        point = Point("parking_slot_state") \
            .tag("slot_id", slot_id) \
            .field("previous_status", previous_status) \
            .field("current_status", current_status) \
            .field("duration", duration) \
            .time(datetime.utcnow(), WritePrecision.NS)
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)



        
    def generate_report(self, start_date, end_date):
        """Genera un report di occupazione tra due date."""
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start_date}, stop: {end_date})
          |> filter(fn: (r) => r._measurement == "event_log")
          |> group(columns: ["slot_id"])
          |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
          |> yield(name: "mean")
        '''
        result = self.client.query_api().query(org=self.org, query=query)
        return result