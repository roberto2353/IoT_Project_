import threading
import cherrypy
import sys
import requests
import json
import time
from pathlib import Path
import paho.mqtt.client as PahoMQTT

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'



class Entrance:
    exposed = True
    def __init__(self, settings):
        self.pubTopic = settings["baseTopic"]
        self.catalog_address = settings['catalog_url']
        self.messageBroker = settings["messageBroker"]
        self.port = settings["brokerPort"]
        self.serviceInfo = settings['serviceInfo']
        self.serviceID = self.serviceInfo['ID']
        self.updateInterval = settings["updateInterval"]
        self.adaptor_url = settings["adaptor_url"]

        self.register_service()

        self._paho_mqtt = PahoMQTT.Client(client_id="EntrancePublisher")
        self._paho_mqtt.connect(self.messageBroker, self.port)
        threading.Thread.__init__(self)
        self.start()

    def start(self):
        """Start the MQTT client."""
        try:
            #self.client.start()  # Start MQTT client connection
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
                    topic = f"ParkingLotFabio/alive/{self.serviceID}"
                    self._paho_mqtt.publish(topic, json.dumps(message))  
                    print(f"Published message to {topic}: {message}")
                    time.sleep(self.updateInterval)
                except Exception as e:
                    print(f"Error during periodic update: {e}")

        # Start periodic updates in a background thread
        update_thread = threading.Thread(target=periodic_update, daemon=True)
        update_thread.start()

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=['POST']) 
    def activate(self):
        try:
            print("RICHIESTA OKS")
            input_data = cherrypy.request.json
            booking_code = input_data.get('booking_code')
            url_ = input_data.get('url')
            port= input_data.get('port')    
            url= f"http://{url_}:{port}/devices"
            name_dev = input_data.get('name')
            print('url:::',url)
            #adaptor_url = 'http://127.0.0.1:8083/devices'  # Updated URL to match the CherryPy server
            response = requests.get(url)
            response.raise_for_status()  

            # Get the list of devices from the adaptor
            slots = response.json()
            #print("slots: ", slots)

            # Assicurati che 'slots' sia un dizionario
            if isinstance(slots, str):
                slots = json.loads(slots)  # Decodifica la stringa JSON manualmente

            # Controlla che 'slots' sia un dizionario e contenga la chiave 'devices'
            if not isinstance(slots, dict) or "devices" not in slots:
                raise ValueError("La risposta JSON non contiene un dizionario valido o manca la chiave 'devices'.")

            devices = slots.get("devices", [])
            print("devices: ", devices)

            # Filter devices with status 'reserved'
            reserved_slots = [device["deviceInfo"] for device in devices if device.get("deviceInfo", {}).get("status") == 'reserved']
            #self.pubTopic = input_data.get('topic')
            print("reserved_slots: ", reserved_slots)


            right_slot = [slot for slot in reserved_slots if slot.get('booking_code') == booking_code]
            print("right_slot: ", right_slot)

            if not right_slot:
                raise cherrypy.HTTPError(400, "Slot not reserved in the system")
            
            selected_device = right_slot[0]  # Assuming the booking code is unique

            # Update the device status via MQTT from 'reserved' to 'occupied'
            sensor_id = selected_device['ID']
            location = selected_device.get('location', 'unknown')
            sensor_type = selected_device.get('type', 'unknown')
            sensor_name = selected_device.get('name', 'unknown')
            print(sensor_name)

            # Create the MQTT message to change the status to "occupied"
            event = {
                "n": f"{sensor_id}/status", 
                "u": "boolean", 
                "t": int(time.time()), 
                "v": 'occupied',  # Change status to 'occupied'
                "sensor_id": sensor_id,
                "location": location,
                "type": sensor_type,
                "booking_code": booking_code,
                "parking":name_dev
            }
            message = {"bn": sensor_name, "e": [event]}
            mqtt_topic_db = f"{self.pubTopic}/{sensor_id}/status"
            mqtt_topic_dc = f"{self.pubTopic}/{name_dev}/{str(selected_device['ID'])}/status"


            # Invio del messaggio MQTT all'adaptor
            self._paho_mqtt.publish(mqtt_topic_db, json.dumps(message))
            self._paho_mqtt.publish(mqtt_topic_dc, json.dumps(message))
            print(f"Messaggio pubblicato sui topic")


            # Successful response to the frontend
            return {
                "message": f"Slot {location} has been successfully occupied.",
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

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    settings = json.load(open(SETTINGS))
    en = Entrance(settings)
    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8085})
    cherrypy.tree.mount(en, '/', conf)
    cherrypy.engine.start()
    #cherrypy.engine.block()
    cherrypy.quickstart(en)