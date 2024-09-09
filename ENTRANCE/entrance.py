import cherrypy
import sys
sys.path.append('/Users/alexbenedetti/Desktop/IoT_Project_')

from DATA.event_logger import EventLogger
import json

class ParkingService:
    def __init__(self):
        
        self.event_logger = EventLogger()

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out() 

    def activate(self):
        try:
            # Ricevi i dati JSON dal corpo della richiesta
            input_data = cherrypy.request.json
            booking_code = input_data.get('booking_code')

            if not booking_code:
                raise cherrypy.HTTPError(400, "Reservation code does not exist in the system")

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
    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8085})
    cherrypy.quickstart(ParkingService())
