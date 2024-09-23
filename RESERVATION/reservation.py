import cherrypy
import sys
import uuid
import requests
import time
from pathlib import Path
import json

from MyMQTT import MyMQTT

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
            catalog = json.load(open(self.catalog_address, "r"))
            body = cherrypy.request.body.read()
            json_body = json.loads(body.decode('utf-8')) if body else {}

            for device in catalog["devices"]:
                if device.get('status') == 'free':
                    booking_code = str(uuid.uuid4())
                    device['status'] = 'occupied'
                    device['booking_code'] = booking_code

                    # Crea e pubblica un messaggio MQTT
                    event = {
                        "n": f"{str(device['ID'])}/status", "u": "boolean", "t": str(time.time()), "v": 'occupied'
                    }
                    message = {"bn": self.pubTopic, "e": [event]}
                    print(f"Messaggio creato: {json.dumps(message)}")

                    # Pubblica il messaggio con MQTT
                    self.client.myPublish(self.pubTopic+'/'+str(device['ID'])+'/status', message)
                    print(f"Messaggio pubblicato su topic {self.pubTopic}/{str(device['ID'])}/status")

                    self.update_catalog_state('occupied', device["ID"])
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

    def update_catalog_state(self, new_state, sensorId):
        conf = json.load(open(SETTINGS))
        catalog_url = conf['catalog_url'] + "/devices"
        try:
            response = requests.get(catalog_url)
            response.raise_for_status()
            devices = response.json().get('devices', [])

            for device in devices:
                if device.get("ID") == sensorId:
                    device["status"] = new_state
                    device["last_update"] = time.time()
                    break

            response = requests.put(catalog_url, json=device)
            response.raise_for_status()
            print(f"Stato del sensore {sensorId} aggiornato nel catalogo a: {new_state}")
        except Exception as e:
            print(f"Errore durante l'aggiornamento del catalogo per il sensore {sensorId}: {e}")

    def start(self):
        """Avvia il client MQTT."""
        self.client.start()  # Avvia la connessione MQTT
        print(f"Publisher connesso al broker {self.messageBroker}:{self.port}")

    def stop(self):
        """Ferma il client MQTT."""
        self.client.stop()

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
