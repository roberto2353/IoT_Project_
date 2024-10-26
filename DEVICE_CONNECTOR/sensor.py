from pathlib import Path
import cherrypy
import requests
import json
import random
import time
import threading
import paho.mqtt.client as PahoMQTT

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'
DEVICES = P / 'setting_status.json'

class SensorREST(threading.Thread):
    exposed = True
    devices_counter=1

    def __init__(self, settings):
        
        self.catalogUrl = settings['catalogURL']
        self.devices = settings['devices']
        self.serviceInfo = settings['serviceInfo']
        self.serviceID = self.serviceInfo['ID']
        #self.first_insertion = True
        self.deviceInfo = []  # Initialize as a list to store multiple device infos
        self.pingInterval = settings["pingInterval"]
        self.updateInterval = settings["updateInterval"]
        self.register_devices()
        
        time.sleep(3)
        self.register_service()
        self.topic = "ParkingLot/alive/"
        self.messageBroker = settings["messageBroker"]
        self.port = settings["brokerPort"]
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

    def register_devices(self):
        for device in self.devices:
            device_info = device['deviceInfo']
            device_info['ID'] = SensorREST.devices_counter
            SensorREST.devices_counter += 1
            if device_info['type'] == 'photocell':
                device_info['commands'] = ['status']
            self.deviceInfo.append(device_info)  # Store device info in a list
            requests.post(f'{self.catalogUrl}/devices', data=json.dumps(device_info))
        print("Devices registered correctly!")

    def register_service(self):
        """Registers the service in the catalog using POST the first time."""
        #Next times, updated with MQTT
        
        # Initial POST request to register the service
        url = f"{self.catalogUrl}/services"
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
                    topic = f"ParkingLot/alive/{self.serviceID}"
                    self._paho_mqtt.publish(topic, json.dumps(message))  
                    print(f"Published message to {topic}: {message}")
                    time.sleep(self.updateInterval)
                except Exception as e:
                    print(f"Error during periodic update: {e}")

        # Start periodic updates in a background thread
        update_thread = threading.Thread(target=periodic_update, daemon=True)
        update_thread.start()

    def run(self):
        while True:
            time.sleep(self.pingInterval)
            self.pingCatalog()
    
    def pingCatalog(self):
        for device in self.deviceInfo:
            location = device["location"]
            message = {
                "bn": "updateCatalogSlot",  
                "e": [
                    {
                        "n": f"{device['ID']}",  
                        "u": "IP",  
                        "t": str(time.time()), 
                        "v": ""  
                    }
                ]
            }
            # Publish the message to the broker
            self._paho_mqtt.publish(self.topic+location, json.dumps(message))
            print(f"Published to topic {self.topic+location}: {json.dumps(message)}")
        print(f"Sensor's update terminated. Next update in {self.pingInterval} seconds")
        
    def load_devs(self):
        """Load the catalog from a JSON file."""
        try:
            with open('C:/Users/kevin/Documents/PoliTo/ProgrammingIOT/IoT_Project_/DEVICE_CONNECTOR/settings_status.json', 'r') as file:
                return(json.load(file))
                
        except Exception as e:
            print(f"Failed to load catalog: {e}")
        
    def GET(self, *uri, **params):
        try:
            if len(uri) == 0:
                raise cherrypy.HTTPError(status=400, message='Invalid URL')
            elif uri[0] == 'devices':
                devices_data = self.load_devs()  # Load the full data structure from JSON
                devices = devices_data.get("devices")  # Extract the list of devices from the dictionary
                
                if isinstance(devices, list):  # Ensure it's a list (expected format)
                    return json.dumps({"devices": devices})
                else:
                    raise ValueError("Invalid data format for devices")
        except Exception as e:
            print(f"Error in GET: {e}")
            raise cherrypy.HTTPError(500, 'no JSON file available')



if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }

    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8083})
    settings = json.load(open(SETTINGS))
    s = SensorREST(settings)
    cherrypy.tree.mount(s, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()