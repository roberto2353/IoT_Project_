import cherrypy
import sys
import requests
import json
import time
from MyMQTT import MyMQTT
from pathlib import Path

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'


class Entrance:
    def __init__(self, baseTopic, broker, port):
        self.pubTopic = f"{baseTopic}"
        self.client = MyMQTT("Entrance", broker, port, None)
        self.messageBroker = broker
        self.port = port

    def start(self):
        """Start the MQTT client."""
        self.client.start()  # Start MQTT client connection
        print(f"Publisher connesso al broker {self.messageBroker}:{self.port}")

    def stop(self):
        """Stop the MQTT client."""
        self.client.stop()  # Stop MQTT client connection

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out() 
    def activate(self):
        try:

            adaptor_url = 'http://127.0.0.1:5000/'  # URL dell'adaptor
            response = requests.get(adaptor_url)
            response.raise_for_status()  # Controlla se la risposta è corretta
            
            # Ottieni la lista dei dispositivi dall'adaptor
            devices = response.json()

            # Filtra i dispositivi con stato 'free'
            reserved_slots = [slot for slot in devices if slot.get('status') == 'reserved']

            input_data = cherrypy.request.json
            booking_code = input_data.get('booking_code')

            right_slot = [slot for slot in reserved_slots if slot.get('booking_code') == booking_code]

            if not right_slot:
                raise cherrypy.HTTPError(400, "Slot does not reserved in the system")
            
            selected_device = right_slot[0]  # Assumendo che il booking code sia unico

            # # Verifica che il tempo non sia maggiore di 20 minuti (1200 secondi)
            # current_time = int(time.time())
            # reservation_time = selected_device.get('time', 0)
            # print(reservation_time, " ", current_time)
            # if current_time - reservation_time > 1200:
            #     raise cherrypy.HTTPError(400, "Reservation expired, more than 20 minutes have passed.")

            # Aggiorna lo stato del dispositivo su MQTT e cambia da 'reserved' a 'occupied'
            sensor_id = selected_device['ID']
            location = selected_device.get('location', 'unknown')
            sensor_type = selected_device.get('type', 'unknown')

            # Creazione del messaggio MQTT per cambiare lo stato su "occupied"
            event = {
                "n": f"{sensor_id}/status", 
                "u": "boolean", 
                "t": int(time.time()), 
                "v": 'occupied',  # Cambiamo lo stato in 'occupied'
                "sensor_id": sensor_id,
                "location": location,
                "type": sensor_type,
                "booking_code": booking_code
            }
            message = {"bn": "Parking System", "e": [event]}
            mqtt_topic = f"{self.pubTopic}/{sensor_id}/status"

            # Invio del messaggio MQTT all'adaptor
            self.client.myPublish(mqtt_topic, json.dumps(message))
            print(f"Messaggio pubblicato su topic {mqtt_topic}")

            # Risposta di successo al frontend
            return {
                "message": f"Slot {location} has been successfully  occupied.",
                "slot_id": sensor_id
            }

        except requests.exceptions.RequestException as e:
            cherrypy.log.error(f"Error during GET request to adaptor: {str(e)}")
            raise cherrypy.HTTPError(500, 'Error communicating with adaptor')

        except json.JSONDecodeError as e:
            cherrypy.log.error(f"JSON error: {str(e)}")
            raise cherrypy.HTTPError(500, 'Error parsing response from adaptor')

        except Exception as e:
            cherrypy.log.error(f"Error during activation process: {str(e)}")
            return {"error": str(e)}, 500
                
                


if __name__ == '__main__':

    conf = json.load(open(SETTINGS))
    baseTopic = conf["baseTopic"]
    broker = conf["messageBroker"]
    port = conf["brokerPort"]
    catalog_url = conf["catalog_url"]

    en = Entrance(baseTopic, broker, port)
    en.start()
    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8085})
    cherrypy.quickstart(en)
