from pathlib import Path
import threading
import cherrypy
import sys
import requests
import json
from datetime import datetime
import time
from MyMQTT import MyMQTT
from pathlib import Path
import pytz
import paho.mqtt.client as PahoMQTT

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'


class Exit:
    def __init__(self, settings):
        self.pubTopic = settings["baseTopic"]
        self.catalog_address = settings['catalog_url']
        self.messageBroker = settings["messageBroker"]
        self.port = settings["brokerPort"]
        self.serviceInfo = settings['serviceInfo']
        self.serviceID = self.serviceInfo['ID']
        self.updateInterval = settings["updateInterval"]
        self.adaptor_url = settings['adaptor_url']

        self.register_service()

        self._paho_mqtt = PahoMQTT.Client(client_id="ExitPublisher")
        self._paho_mqtt.connect(self.messageBroker, self.port)
        threading.Thread.__init__(self)
        self.start()

    def start_periodic_updates(self):
        """
        Starts a background thread that publishes periodic updates via MQTT.
        """
        def periodic_update():
            time.sleep(10)
            while True:
                try:
                    message = {
                        "bn": "updateCatalogService",  
                        "e": [
                            {
                                "n": f"{self.serviceID}",  
                                "u": "IP",  
                                "t": str(time.time()), 
                                "v": ""  
                            }
                        ]
                    }
                    topic = f"ParkingLot/alive/{self.serviceID}"
                    self._paho_mqtt.publish(topic, json.dumps(message))  
                    print(f"Published message to {topic}: {message}")
                    time.sleep(self.updateInterval)
                except Exception as e:
                    print(f"Error during periodic update: {e}")

        # Start periodic updates in a background thread
        update_thread = threading.Thread(target=periodic_update, daemon=True)
        update_thread.start()

    def start(self):
        """Start the MQTT client."""
        try:
            self.client.start()  # Start MQTT client connection
            print(f"Publisher connected to broker {self.messageBroker}:{self.port}")
            self.start_periodic_updates()
        except Exception as e:
            print(f"Error starting MQTT client: {e}")

    def stop(self):
        """Stop the MQTT client."""
        try:
            self.client.stop()  # Stop MQTT client connection
        except Exception as e:
            print(f"Error stopping MQTT client: {e}")

    def register_service(self):
        """Registers the service in the catalog using POST the first time."""
        #Next times, updated with MQTT
        
        # Initial POST request to register the service
        url = f"{self.catalog_address}/services"
        response = requests.post(url, json=self.serviceInfo)
        if response.status_code == 200:
            self.is_registered = True
            print(f"Service {self.serviceID} registered successfully.")
        else:
            print(f"Failed to register service: {response.status_code} - {response.text}")

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out() 
    def exit(self):
        try:

            #adaptor_url = 'http://127.0.0.1:5001/'  # URL dell'adaptor
            response = requests.get(self.adaptor_url)
            response.raise_for_status()  # Controlla se la risposta è corretta
            
            # Ottieni la lista dei dispositivi dall'adaptor
            devices = response.json()

            print("AS: ", devices)

            # Filtra i dispositivi con stato 'free'
            occupied_slots = [slot for slot in devices if slot.get('status') == 'occupied']

            print("OS: ", occupied_slots)

            input_data = cherrypy.request.json
            booking_code = input_data.get('booking_code')



            right_slot = [slot for slot in occupied_slots if slot.get('booking_code') == booking_code]

            if not right_slot:
                raise cherrypy.HTTPError(400, "Slot does not occupied in the system")
            
            selected_device = right_slot[0]  # Assumendo che il booking code sia unico


            # Aggiorna lo stato del dispositivo su MQTT e cambia da 'reserved' a 'occupied'
            sensor_id = selected_device['ID']
            location = selected_device.get('location', 'unknown')
            sensor_type = selected_device.get('type', 'unknown')
            sensor_name = selected_device.get('name', 'unknown')
            booking_start_time_str = selected_device.get('time', None)
            
            if booking_start_time_str is None:
                raise cherrypy.HTTPError(500, 'Booking start time not found')
            
            booking_start_time = datetime.strptime(booking_start_time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)

            
            #booking_start_timestamp = int(booking_start_time.timestamp())

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            current_time_ok = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
            
            print("current_time: ", current_time_ok, "booking_start_time: " ,booking_start_time)
            parking_duration_seconds = (current_time_ok - booking_start_time).total_seconds()
            parking_duration_hours = parking_duration_seconds / 3600 # Converti i secondi in ore

            print("parking_duration_hours :", parking_duration_hours)

            if parking_duration_hours <= 10:
                fee = parking_duration_hours * 2  # 2 euro per ora
            else:
                # Se supera le 10 ore, calcola 20 euro ogni 24 ore (giorno intero)
                full_days = int(parking_duration_hours // 24)  # Numero di giorni interi
                remaining_hours = parking_duration_hours % 24  # Ore rimanenti dopo giorni interi
                fee = full_days * 20 + (remaining_hours * 2 if remaining_hours <= 10 else 20)

            # Creazione del messaggio MQTT per cambiare lo stato su "occupied"
            event = {
                "n": f"{sensor_id}/status", 
                "u": "boolean", 
                "t": int(time.time()), 
                "v": 'free', 
                "sensor_id": sensor_id,
                "location": location,
                "type": sensor_type,
                "booking_code": booking_code
            }
            message = {"bn": sensor_name, "e": [event]}
            mqtt_topic = f"{self.pubTopic}/{sensor_id}/status"

            # Invio del messaggio MQTT all'adaptor
            self.client.myPublish(mqtt_topic, json.dumps(message))
            print(f"Messaggio pubblicato su topic {mqtt_topic}")

            # Risposta di successo al frontend
            return {
                "message": f"Slot {location} has been successfully  became free.",
                "slot_id": sensor_id,
                "parking_duration": str(parking_duration_hours),
                "parking_fee": fee
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

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    settings = json.load(open(SETTINGS))
    ex = Exit(settings)
    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8056})
    cherrypy.tree.mount(ex, '/', conf)
    cherrypy.engine.start()
    #cherrypy.engine.block()
    cherrypy.quickstart(ex)
