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
    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8085})
    cherrypy.quickstart(ParkingService())
