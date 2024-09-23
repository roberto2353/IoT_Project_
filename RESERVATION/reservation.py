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
        self.catalog_address = 'C:/Users/kevin/Documents/PoliTo/ProgrammingIOT/IoT_Project_/CATALOG/catalog.json'
        self.pubTopic = f"{baseTopic}"
        self.client = MyMQTT("Reservation", broker, port, None)
        self.messageBroker = broker
        self.port = port

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def book(self):
        try:
            # Carica il catalogo
            catalog = json.load(open(self.catalog_address, "r"))

            # Inizializza l'algoritmo con la lista di dispositivi (devices)
            devices = catalog["devices"]
            algorithm = Algorithm(devices)

            # Aggiorna le informazioni sui dispositivi (occupazione per piano, ecc.)
            algorithm.countFloors()
            algorithm.countDev()
            algorithm.devPerFloorList()
            algorithm.occDevPerFloorList()
            algorithm.totalOccupied()

            # Usa routeArrivals per selezionare un dispositivo da occupare
            selected_device = algorithm.routeArrivals()
            if selected_device:
                # Crea un codice di prenotazione
                booking_code = str(uuid.uuid4())
                selected_device['status'] = 'occupied'
                selected_device['booking_code'] = booking_code
                selected_device['last_update'] = time.time()

                # Crea e pubblica il messaggio MQTT
                event = {
                    "n": f"{str(selected_device['ID'])}/status", "u": "boolean", "t": str(time.time()), "v": 'occupied'
                }
                message = {"bn": self.pubTopic, "e": [event]}
                print(f"Messaggio creato: {json.dumps(message)}")

                self.client.myPublish(self.pubTopic + '/' + str(selected_device['ID']) + '/status', message)
                print(f"Messaggio pubblicato su topic {self.pubTopic}/{str(selected_device['ID'])}/status")

                # Aggiorna il catalogo dopo aver prenotato lo slot
                with open(self.catalog_address, 'w') as f:
                    json.dump(catalog, f, indent=4)

                return {
                    "message": f"Slot {selected_device['location']} has been successfully booked.",
                    "booking_code": booking_code
                }
            else:
                return {"message": "No free slots available at the moment."}

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

    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8088})
    cherrypy.quickstart(res)
