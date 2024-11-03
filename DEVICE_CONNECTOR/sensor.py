import datetime
from pathlib import Path
import cherrypy
import requests
import json
import random
import time
import threading
import paho.mqtt.client as PahoMQTT
from entranceAlgorithm import Algorithm, EntranceAlgorithmService

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'
DEVICES = P / 'setting_status.json'

class SensorREST(threading.Thread):
    exposed = True
    devices_counter=1

<<<<<<< HEAD
    def __init__(self, settings):
        #super().__init__()
=======
    def __init__(self, settings, status):
        super().__init__()  # Corretto inizializzazione del thread
>>>>>>> 58912435b20f8f5db07da31845dc4ec38181ca09
        self.catalogUrl = settings['catalogURL']
        self.devices = settings['devices']
        self.devices_status = status['devices']
        self.setting_status_path = P / 'settings_status.json'
        self.serviceInfo = settings['serviceInfo']
        self.parkingInfo = settings['parkingInfo']
        self.serviceID = self.serviceInfo['ID']
        self.deviceInfo = []  # Initialize as a list to store multiple device infos
        self.pingInterval = settings["pingInterval"]
        self.updateInterval = settings["updateInterval"]
        self.register_devices()
        
        # Inizializzazione dell'algoritmo di parcheggio
        broker = settings["messageBroker"]
        port = settings["brokerPort"]
        baseTopic = settings["baseTopic"]
        # self.algorithm = Algorithm(self.devices, baseTopic, broker, port)
        # self.algorithm.start()

        self.entranceAlgorithmService = EntranceAlgorithmService()
        self.entranceAlgorithmService.algorithm.start()
        self.entranceAlgorithmService.sim_loop_start()

        threading.Thread(target=self.entranceAlgorithmService.algorithm.simulate_arrivals_loop, daemon=True).start()  # Avvia simulazione

        time.sleep(3)
        self.register_service()
        self.register_parking()
        
        self.topic = "ParkingLot/alive/"
        self.messageBroker = broker
        self.port = port
        self._paho_mqtt = PahoMQTT.Client(client_id="EntrancePublisher_K")
        self._paho_mqtt.connect(self.messageBroker, self.port)
        threading.Thread(target=self.pingCatalog, daemon=True).start()
<<<<<<< HEAD
        self.start()
        #self.run()
=======

        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

        self.start()
    
    # @cherrypy.expose
    # @cherrypy.tools.json_out()
    # @cherrypy.tools.allow(methods=['GET'])
    # def get_best_parking(self):
    #     """Ottiene il miglior parcheggio disponibile utilizzando l'algoritmo."""
    #     print("richiesta arrivata")
    #     return self.entranceAlgorithmService.algorithm.routeArrivals(get='True')
>>>>>>> 58912435b20f8f5db07da31845dc4ec38181ca09

    
    def start(self):
        """Start the MQTT client."""
        try:
            #self.client.start()  # Start MQTT client connection
            print(f"Publisher connected to broker {self.messageBroker}:{self.port}")
            self.start_periodic_updates()
            self._paho_mqtt.subscribe('ParkingLot/DevConnector1/+/status', 2)
            self._paho_mqtt.loop_start()
            print(f"Publisher connected to broker {self.messageBroker}:{self.port}")
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

    #def run(self):
    #    while True:
    #        time.sleep(self.pingInterval)
    #        self.pingCatalog()
    
    def pingCatalog(self):
        while True:
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
                print(self.topic+location)
                self._paho_mqtt.publish(self.topic+location, json.dumps(message))
                print(f"Published to topic {self.topic+location}: {json.dumps(message)}")
            print(f"Sensor's update terminated. Next update in {self.pingInterval} seconds")
            time.sleep(self.pingInterval)
        
    def load_devs(self):
        """Load the catalog from a JSON file."""
        try:
<<<<<<< HEAD
            with open(SETTINGS, 'r') as file:
=======
            #with open('C:/Users/kevin/Documents/PoliTo/ProgrammingIOT/IoT_Project_/DEVICE_CONNECTOR/settings_status.json') as file:
            with open(DEVICES, 'r') as file:    
>>>>>>> 58912435b20f8f5db07da31845dc4ec38181ca09
                return(json.load(file))
                
        except Exception as e:
            print(f"Failed to load catalog: {e}")
    
    def register_parking(self):

        #Next times, updated with MQTT
        url = f"{self.catalogUrl}/parkings"
        response = requests.post(url, json=self.parkingInfo)
        if response.status_code == 200:
            #self.is_registered = True
            print(f"Parking 1 registered successfully.")
        else:
            print(f"Failed to register service: {response.status_code} - {response.text}")

    @cherrypy.expose
    @cherrypy.tools.json_out()
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
            elif uri[0] == 'get_best_parking':
                print("Richiesta per 'get_best_parking' ricevuta")
                return self.entranceAlgorithmService.algorithm.routeArrivals(get='True')
            else:
                raise cherrypy.HTTPError(status=404, message='Endpoint non trovato')
        except Exception as e:
            print(f"Error in GET: {e}")
            raise cherrypy.HTTPError(500, 'no JSON file available')
        
    def recursive_json_decode(self, data):
        # Prova a decodificare fino a ottenere un dizionario o una lista
        while isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                break
        return data
    
    def myOnConnect(self, paho_mqtt, userdata, flags, reasonCode, properties=None):
        print(f"Connected to {self.messageBroker} with result code: {reasonCode}")
        
    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        # Un nuovo messaggio viene ricevuto
        print(f"ARRIVED!!!!!!!!! Topic: '{msg.topic}', QoS: '{msg.qos}', Message: '{msg.payload.decode()}'")
        
        try:
            # Decodifica del payload JSON una prima volta
            decoded_message = msg.payload.decode()
            print(f"Decoded message (first decode): {decoded_message}")

            # Decodifica ricorsiva fino a ottenere un dizionario o una lista
            final_data = self.recursive_json_decode(decoded_message)
            print(f"Final decoded message: {final_data}")
            print(f"Data type after final decode: {type(final_data)}")

            # Assicurati che 'final_data' sia un dizionario
            if isinstance(final_data, dict):
                print("E SIAMO QUA'''")
                data = final_data
                event = data.get('e', [])[0]
                print(f"Extracted event: {event}")

                # Estrai i dettagli dell'evento
                sensor_id = event.get('sensor_id', '')
                status_ = event.get('v', 'unknown')  # Recupera lo stato
                location = event.get('location', 'unknown')
                sensor_type = event.get('type', 'unknown')
                booking_code = event.get('booking_code', '')
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Carica i dati esistenti
                with open(self.setting_status_path, 'r') as f:
                    data = json.load(f)

                # Trova e aggiorna solo il dispositivo specifico
                for dev in data["devices"]:
                    if dev["deviceInfo"]['ID'] == sensor_id:
                        dev["deviceInfo"]['status'] = status_
                        dev["deviceInfo"]['last_update'] = current_time
                        dev["deviceInfo"]['booking_code'] = booking_code
                        print(status_)
                        break  # Esce dal ciclo una volta trovato il dispositivo

                # Riscrivi solo il dispositivo aggiornato nel file
                with open(self.setting_status_path, 'w') as f:
                    json.dump(data, f, indent=4)

            else:
                print(f"Final data is not a dictionary: {type(final_data)}")

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        
        except Exception as e:
            print(f"Error processing message: {e}")

        





if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
<<<<<<< HEAD
            'tools.encode.on': True, 
=======
>>>>>>> 58912435b20f8f5db07da31845dc4ec38181ca09
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        }
    }

    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8083})
    #status = json.load(open('C:/Users/kevin/Documents/PoliTo/ProgrammingIOT/IoT_Project_/DEVICE_CONNECTOR/settings_status.json'))
    #settings = json.load(open('C:/Users/kevin/Documents/PoliTo/ProgrammingIOT/IoT_Project_/DEVICE_CONNECTOR/settings.json'))
    settings = json.load(open(SETTINGS))
    status = json.load(open(DEVICES))
    s = SensorREST(settings,status)
    cherrypy.tree.mount(s, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()