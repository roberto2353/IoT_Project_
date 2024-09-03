import cherrypy
import sys

sys.path.append('/Users/alexbenedetti/Desktop/IoT_Project_')

from DATA.event_logger import EventLogger
from datetime import datetime, timedelta
import json

class ParkingExitService:

    def __init__(self):
        self.event_logger = EventLogger()

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
              |> filter(fn: (r) => r._measurement == "parking_slot_state" and r.slot_id == "{booking_code}" and r.current_status == "occupied")
              |> last()
            '''

            result = self.event_logger.client.query_api().query(org=self.event_logger.org, query=query)

            if not result or len(result[0].records) == 0:
                raise cherrypy.HTTPError(404, "Evento di entrata non trovato")

            entry_time = result[0].records[0].get_time()

            exit_time = datetime.utcnow()
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
    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8086})
    cherrypy.quickstart(ParkingExitService())
