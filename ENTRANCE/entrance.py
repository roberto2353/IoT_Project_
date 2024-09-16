import cherrypy
import sys
import time
import requests
import threading

sys.path.append('/Users/robertobratu/Desktop/IoT_Project_')

from DATA.event_logger import EventLogger
import json

class ParkingService:
    def __init__(self, settings='settings.json'):
        with open(settings, 'r') as f:
            self.service = json.load(f)
        

        self.catalog_address = self.service["catalogURL"]
        self.update_interval = self.service["updateInterval"]
        self.service_info = self.service["serviceInfo"]
        self.service_info["last_update"] = time.time() 
        self.is_registered = False

        self.event_logger = EventLogger()

        self.start_periodic_updates()

    def register_service(self):
        """Registers the service in the catalog using POST the first time.
        For subsequent updates, it uses PUT."""
        try:
            if not self.is_registered:
                # Initial POST request to register the service
                url = f"{self.catalog_address}/services"
                response = requests.post(url, json=self.service_info)
                if response.status_code == 200:
                    self.is_registered = True
                    print(f"Service {self.service_info['ID']} registered successfully.")
                else:
                    print(f"Failed to register service: {response.status_code} - {response.text}")
            else:
                # Subsequent PUT requests to update the service info (timestamp)
                url = f"{self.catalog_address}/services"
                self.service_info["last_update"] = time.time()  # Update timestamp
                response = requests.put(url, json=self.service_info)
                if response.status_code == 200:
                    print(f"Service {self.service_info['ID']} updated successfully.")
                else:
                    print(f"Failed to update service: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error during service registration/update: {e}")
    
    def start_periodic_updates(self):
        """
        Starts a background thread that sends periodic updates to the catalog.
        """
        def periodic_update():
            while True:
                self.register_service()
                time.sleep(self.update_interval)

        # Start periodic updates in a background thread
        update_thread = threading.Thread(target=periodic_update, daemon=True)
        update_thread.start()

    

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out() 

    def activate(self):
        try:
            # Ricevi i dati JSON 
            input_data = cherrypy.request.json
            booking_code = input_data.get('booking_code')

            if not booking_code:
                raise cherrypy.HTTPError(400, "Reservation code does not exist in the system")
            
            query = f'''
            from(bucket: "{self.event_logger.bucket}")
              |> range(start: -24h)  // Puoi modificare l'intervallo di tempo se necessario
              |> filter(fn: (r) => r._measurement == "parking_slot_state" and r.slot_id == "{booking_code}" and r._field == "current_status" and r._value == "reserved")
              |> last()
            '''

            result = self.event_logger.client.query_api().query(org=self.event_logger.org, query=query)

            if not result or len(result[0].records) == 0:
                raise cherrypy.HTTPError(404, "Evento di prenotazione non trovato")
            else:
                # Logga l'evento di "entrata" in InfluxDB
                self.event_logger.log_event(
                    slot_id=booking_code,
                    previous_status= "reserved",
                    current_status= "occupied",
                    duration = 0.0  # Il tempo di permanenza sarà calcolato al momento dell'uscita
                )

                return {"message": f"Parking {booking_code} succesfully activated!"}

        except cherrypy.HTTPError as e:
            raise e 
        except Exception as e:
            cherrypy.response.status = 500
            return {"error": str(e)}

if __name__ == '__main__':
    

    #cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8085})
    #cherrypy.quickstart(ParkingService(settings="settings.json"), config=conf)

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    p = ParkingService("settings.json")

    cherrypy.config.update({'server.socket_host': 'localhost', 'server.socket_port': 8085})
    cherrypy.tree.mount(p, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()