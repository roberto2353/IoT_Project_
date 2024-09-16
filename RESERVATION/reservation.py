import threading
import time
import cherrypy
import sys
import uuid
import requests
sys.path.append('/Users/robertobratu/Desktop/IoT_Project_')

from DATA.event_logger import EventLogger
import json

class ReservationService:
    def __init__(self, settings="settings.json"):
        with open(settings, 'r') as f:
            self.service = json.load(f)

        self.catalog_address = self.service["catalogURL"] + "/services"
        self.update_interval = self.service["updateInterval"]
        self.service_info = self.service["serviceInfo"]
        self.service_info["last_update"] = time.time()
        self.is_registered = False


        self.event_logger = EventLogger()
        self.start_periodic_updates()

    def register_service(self):
            """Registers the parking service in the catalog using POST the first time. For subsequent updates, it uses PUT."""
            try:
                if not self.is_registered:
                # Initial POST request to register the service
                    url = f"{self.catalog_address}"
                    response = requests.post(url, json=self.service_info)
                    if response.status_code == 200:
                        self.is_registered = True
                        print(f"Service {self.service_info['ID']} registered successfully.")
                    else:
                        print(f"Failed to register service: {response.status_code} - {response.text}")
                else:
                # Subsequent PUT requests to update the service info (timestamp)
                    url = f"{self.catalog_address}"
                    self.service_info["last_update"] = time.time()
                    response = requests.put(url, json=self.service_info)
                    if response.status_code == 200:
                        print(f"Service {self.service_info['ID']} updated successfully.")
                    else:
                        print(f"Failed to update service: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Error during service registration/update: {e}")

    def start_periodic_updates(self):
        """Starts a background thread that sends periodic updates to the catalog."""
        def periodic_update():
            while True:
                self.register_service()
                time.sleep(self.update_interval)

        # Start periodic updates in a background thread
        update_thread = threading.Thread(target=periodic_update, daemon=True)
        update_thread.start()

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def book(self):
        try:
            catalog = json.load(open(self.catalog_address, "r"))
            body = cherrypy.request.body.read()
            json_body = json.loads(body.decode('utf-8')) if body else {}

            for device in catalog["devices"]:
                if device.get('status') == 'free':
                    booking_code = str(uuid.uuid4())
                    device['status'] = 'occupied'
                    device['booking_code'] = booking_code
                    json.dump(catalog, open(self.catalog_address, "w"), indent=4)
                    return {
                        "message": f"Slot {device['location']} has been successfully booked.",
                        "booking_code": booking_code
                    }

            return {"message": "No free slots available at the moment."}

        except json.JSONDecodeError as e:
            cherrypy.log.error(f"JSON error: {str(e)}")
            raise cherrypy.HTTPError(500, 'JSON PARSE ERROR')

        except Exception as e:
            cherrypy.log.error(f"Error during POST request handling: {str(e)}")
            raise cherrypy.HTTPError(500, 'INTERNAL SERVER ERROR')


if __name__ == '__main__':
    #cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8088})
    #cherrypy.quickstart(ParkingService("settings.json"))

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    p = ReservationService("settings.json")

    cherrypy.config.update({'server.socket_host': 'localhost', 'server.socket_port': 8088})
    cherrypy.tree.mount(p, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()