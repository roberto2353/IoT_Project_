import cherrypy
import sys
import uuid
sys.path.append('/Users/alexbenedetti/Desktop/IoT_Project_')

from DATA.event_logger import EventLogger
import json

class ParkingService:
    def __init__(self):
        
        self.event_logger = EventLogger()
        self.catalog_address = '/Users/alexbenedetti/Desktop/IoT_Project_/CATALOG/catalog.json'

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
    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8088})
    cherrypy.quickstart(ParkingService())