import datetime
import cherrypy
import sys
import uuid
import requests
import time
from pathlib import Path
import json
from MyMQTT import MyMQTT

# Import the Algorithm class from the entranceAlgorithm file
from entranceAlgorithm import Algorithm  

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class ParkingService:
    def __init__(self, baseTopic, broker, port):
        #self.catalog_address = 'C:/Users/kevin/Documents/PoliTo/ProgrammingIOT/IoT_Project_/CATALOG/catalog.json'
        self.pubTopic = f"{baseTopic}"
        self.client = MyMQTT("Reservation", broker, port, None)
        self.messageBroker = broker
        self.port = port

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    @cherrypy.tools.json_out()
    def book(self):

        print("Siamo in reservation")
        try:
            # Effettua una richiesta GET all'adaptor per ottenere i dispositivi
            adaptor_url = 'http://127.0.0.1:5001/'  # URL dell'adaptor
            response = requests.get(adaptor_url)
            response.raise_for_status()  # Controlla se la risposta è corretta
            
            # Ottieni la lista dei dispositivi dall'adaptor
            devices = response.json()
            
            # Inizializza l'algoritmo con la lista di dispositivi
            algorithm = Algorithm(devices)

            # Aggiorna le informazioni sui dispositivi (occupazione per piano, ecc.)
            algorithm.countFloors()
            algorithm.countDev()
            algorithm.devPerFloorList()
            algorithm.occDevPerFloorList()
            algorithm.totalOccupied()

            # Recalculate the occupancy per floor based on the updated catalog
            #algorithm.handle_departures(catalog_path)  
            algorithm.arrival_time()
            algorithm.routeArrivals()

            # Usa routeArrivals per selezionare un dispositivo da occupare
            selected_device = algorithm.routeArrivals()
            print("OOOK SELECTED: ", selected_device)
            if selected_device:
                # Crea un codice di prenotazione
                booking_code = str(uuid.uuid4())
                selected_device['status'] = 'occupied'
                selected_device['booking_code'] = booking_code
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                selected_device['last_update'] = str(current_time)

                reservation_url = 'http://127.0.0.1:5001/reservation'
                headers = {'Content-Type': 'application/json'}
                reservation_data = {
                    "ID": selected_device['ID'],
                    "name": selected_device.get('name', 'unknown'),
                    "type": selected_device.get('type', 'unknown'),
                    "location": selected_device.get('location', 'unknown'),
                    "booking_code": booking_code
                }
                reservation_response = requests.post(reservation_url, headers=headers, data=json.dumps(reservation_data))
                reservation_response.raise_for_status()

                # Crea e pubblica un messaggio MQTT
                event = {
                    "n": f"{str(selected_device['ID'])}/status", "u": "boolean", "t": str(time.time()), "v": 'reserved',
                    "sensor_id": selected_device['ID'],
                    "location": selected_device.get('location', 'unknown'),
                    "type": selected_device.get('type', 'unknown'),
                    "booking_code": booking_code
                }
                message = {"bn": self.pubTopic, "e": [event]}
                print(f"Messaggio creato: {json.dumps(message, indent=4)}")

                # Pubblica il messaggio MQTT
                self.client.myPublish(self.pubTopic + '/' + str(selected_device['ID']) + '/status', message)
                print(f"Messaggio pubblicato su topic {self.pubTopic}/{str(selected_device['ID'])}/status")

                return {
                    "message": f"Slot {selected_device['location']} has been successfully booked.",
                    "booking_code": booking_code,
                    "slot_id": selected_device['ID']
                }
            else:
                return {"message": "No free slots available at the moment."}

        except requests.exceptions.RequestException as e:
            cherrypy.log.error(f"Error during GET request to adaptor: {str(e)}")
            raise cherrypy.HTTPError(500, 'ERROR GETTING DEVICES FROM ADAPTOR')

        except json.JSONDecodeError as e:
            cherrypy.log.error(f"JSON error: {str(e)}")
            raise cherrypy.HTTPError(500, 'JSON PARSE ERROR')

        except Exception as e:
            cherrypy.log.error(f"Error during POST request handling: {str(e)}")
            raise cherrypy.HTTPError(500, 'INTERNAL SERVER ERROR')


    def start(self):
        """Start the MQTT client."""
        self.client.start()  # Start MQTT client connection
        print(f"Publisher connesso al broker {self.messageBroker}:{self.port}")

    def stop(self):
        """Stop the MQTT client."""
        self.client.stop()  # Stop MQTT client connection

if __name__ == '__main__':
    conf = json.load(open(SETTINGS))
    baseTopic = conf["baseTopic"]
    broker = conf["messageBroker"]
    port = conf["brokerPort"]
    catalog_url = conf["catalog_url"]

    res = ParkingService(baseTopic, broker, port)
    res.start()

    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8098})
    cherrypy.quickstart(res)
