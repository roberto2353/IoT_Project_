import cherrypy
import sys
import pytz
from datetime import datetime, timedelta, timezone
import time

sys.path.append('/Users/robertobratu/Desktop/IoT_Project_')

from DATA.event_logger import EventLogger
from datetime import datetime, timedelta
import json
import requests
import threading
import paho.mqtt.client as PahoMQTT

class ParkingExitService:

    def __init__(self, settings="settings.json"):
        with open(settings, 'r') as f:
            self.service = json.load(f)

        self.catalog_address = self.service["catalogURL"] + "/services"
        self.update_interval = self.service["updateInterval"]
        self.service_info = self.service["serviceInfo"]
        self.service_info["last_update"] = time.time()

        self.clientID = "ExitPublisher"
        self.mqtt_broker = self.service['messageBroker']
        self.mqtt_port = self.service['brokerPort']

        self.event_logger = EventLogger()
        self.register_service()

        self.mqtt_client = PahoMQTT.Client(client_id=self.clientID)
        self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port)  # Replace with your MQTT broker address
        self.mqtt_client.loop_start()

        self.start_periodic_updates()

    def register_service(self):
        """Registers the exit service in the catalog using POST the first time"""
            
        # Initial POST request to register the service
        url = f"{self.catalog_address}"
        response = requests.post(url, json=self.service_info)
        if response.status_code == 200:
            self.is_registered = True
            print(f"Service {self.service_info['ID']} registered successfully.")
        else:
            print(f"Failed to register service: {response.status_code} - {response.text}")
            

    def start_periodic_updates(self):
        """
        Starts a background thread that publishes periodic updates via MQTT.
        """
        def periodic_update():
            while True:
                message = {
                    "bn": "updateCatalogService",  
                    "e": [
                        {
                            "n": f"{self.service_info['ID']}",  
                            "u": "IP",  
                            "t": str(time.time()), 
                            "v": ""  
                        }
                    ]
                }
                topic = f"ParkingLot/alive/{self.service_info['name']}"
                self.mqtt_client.publish(topic, json.dumps(message))
                print(f"Published message to {topic}: {message}")
                time.sleep(self.update_interval)

        # Start periodic updates in a background thread
        update_thread = threading.Thread(target=periodic_update, daemon=True)
        update_thread.start()

    def calculate_parking_fee(self, parking_duration):
        hourly_rate = 2.0
        reduced_rate = 12.0 
        daily_rate = 20.0 

        if parking_duration > timedelta(hours=12):
            return daily_rate
        elif parking_duration > timedelta(hours=6):
            return reduced_rate
        else:
            hours_parked = parking_duration.total_seconds() / 3600
            return round(hours_parked * hourly_rate, 2)

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def exit(self):
        try:
            input_data = cherrypy.request.json
            booking_code = input_data.get('booking_code')

            if not booking_code:
                raise cherrypy.HTTPError(400, "Codice di prenotazione mancante")

            query = f'''
            from(bucket: "{self.event_logger.bucket}")
              |> range(start: -24h)  // Puoi modificare l'intervallo di tempo se necessario
              |> filter(fn: (r) => r._measurement == "parking_slot_state" and r.slot_id == "{booking_code}" and r._field == "current_status" and r._value == "occupied")
              |> last()
            '''

            result = self.event_logger.client.query_api().query(org=self.event_logger.org, query=query)

            if not result or len(result[0].records) == 0:
                raise cherrypy.HTTPError(404, "Evento di entrata non trovato")

            
            entry_time = result[0].records[0].get_time().replace(tzinfo=pytz.UTC)

            
            exit_time = datetime.utcnow().replace(tzinfo=pytz.UTC)

            self.event_logger.log_event(
                slot_id=booking_code,
                previous_status="occupied",
                current_status="available",
                duration=(exit_time - entry_time).total_seconds()
            )

            parking_duration = exit_time - entry_time
            parking_fee = self.calculate_parking_fee(parking_duration)

            return {
                "message": f"Codice {booking_code} elaborato con successo!",
                "parking_duration": str(parking_duration),
                "parking_fee": parking_fee
            }

        except cherrypy.HTTPError as e:
            raise e
        except Exception as e:
            cherrypy.response.status = 500
            return {"error": str(e)}

if __name__ == '__main__':
    #cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8087})
    #cherrypy.quickstart(ParkingExitService("settings.json"))

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    p = ParkingExitService("settings.json")

    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8087})
    cherrypy.tree.mount(p, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()