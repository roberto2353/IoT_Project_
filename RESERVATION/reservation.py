from pathlib import Path
import threading
import cherrypy
import requests
import uuid
import time
import json
from MyMQTT import MyMQTT
from datetime import datetime
import paho.mqtt.client as PahoMQTT

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class ReservationService:
    exposed = True
    def __init__(self, settings):
        self.pubTopic = settings["baseTopic"]
        self.catalog_address = settings['catalog_url']
        self.messageBroker = settings["messageBroker"]
        self.port = settings["brokerPort"]
        self.serviceInfo = settings['serviceInfo']
        self.serviceID = self.serviceInfo['ID']
        self.updateInterval = settings["updateInterval"]
        self.adaptor_url = settings['adaptor_url']
        self.device_connector_url = settings["devConn_url"]

        self.entrance_algorithm_url = "http://127.0.0.1:8081/get_best_parking"
        self.register_service()

        self._paho_mqtt = PahoMQTT.Client()
        self.client = MyMQTT("Reservation_Kev", self.messageBroker, self.port, None)

        self._paho_mqtt.connect(self.messageBroker, self.port)
        threading.Thread.__init__(self)
        self.start()

    def start(self):
        """Start the MQTT client."""
        try:
            #self.client.start()  # Start MQTT client connection
            print(f"Publisher connected to broker {self.messageBroker}:{self.port}")
            self.start_periodic_updates()
            self.client.start()
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
                    topic = f"ParkingLot/alive/{self.serviceID}"
                    self._paho_mqtt.publish(topic, json.dumps(message))  
                    print(f"Published message to {topic}: {message}")
                    time.sleep(self.updateInterval)
                except Exception as e:
                    print(f"Error during periodic update: {e}")

        # Start periodic updates in a background thread
        update_thread = threading.Thread(target=periodic_update, daemon=True)
        update_thread.start()

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def book(self):
        print("CIaoo")
        try:
            data = cherrypy.request.json
            booking_code = data['booking_code']
            url = data['url']
            dev_name = data['name']
            print("passed: booking_code ", booking_code)
            print("passed: url ", url)
            response = requests.get(url)
            if response.status_code == 200:
                print(response.json())
                selected_device_ = response.json().get("parking")
                selected_device = selected_device_.get("deviceInfo", {})
                print(f"selected device for current booking: {selected_device['ID']}")
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if selected_device:
                    # Create a booking code
                    if booking_code == "":
                        booking_code_ = str(uuid.uuid4())
                        booking_code = booking_code_[:6]
                    selected_device['status'] = 'reserved'
                    selected_device['booking_code'] = booking_code
                    selected_device['last_update'] = str(current_time)

                    # # Send reservation data to adaptor
                    # reservation_url = 'http://127.0.0.1:5000/reservation'
                    # headers = {'Content-Type': 'application/json'}
                    # reservation_data = {
                    #     "ID": selected_device['ID'],
                    #     "name": selected_device.get('name', 'unknown'),
                    #     "type": selected_device.get('type', 'unknown'),
                    #     "location": selected_device.get('location', 'unknown'),
                    #     "booking_code": booking_code
                    # }
                    # requests.post(reservation_url, headers=headers, json=reservation_data)

                    event = {
                "n": f"{selected_device['ID']}/status", 
                "u": "boolean", 
                #"t": str(datetime.datetime.now()), 
                "v": selected_device['status'],  # Cambiamo lo stato in 'reserved'
                "sensor_id": selected_device['ID'],
                "location": selected_device['location'],
                "type": selected_device['type'],
                "booking_code": selected_device['booking_code'],
                #"floor": self.extract_floor(selected_device['location'])
                "parking":dev_name
                }
            
                    message = {"bn": selected_device['name'], "e": [event]}
                    mqtt_topic_db = f"{self.pubTopic}/{str(selected_device['ID'])}/status"
                    mqtt_topic_dc = f"{self.pubTopic}/{dev_name}/{str(selected_device['ID'])}/status"


        # Invio del messaggio MQTT all'adaptor
                    self.client.myPublish(mqtt_topic_db, json.dumps(message))
                    self.client.myPublish(mqtt_topic_dc, json.dumps(message))
                    print(f"Messaggio pubblicato sul topic ",mqtt_topic_dc)


                    if booking_code.isupper():
                        url = 'http://127.0.0.1:8085/activate'

                        # Dati da inviare nella richiesta
                        data = {
                            "booking_code": booking_code,
                            "url":data['url'],
                            "port":data['port'],
                            "name":data['name']

                        }

                        # Invio della richiesta POST
                        response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))

                        # Stampa la risposta del server
                        #print(f"Status Code: {response.status_code}")

                        return {
                        "message": f"Go to the parking slot: {selected_device['location']}.",
                        "booking_code": booking_code,
                        "slot_id": selected_device['ID'],
                        "type": selected_device.get('type', 'unknown'),
                        "name": selected_device.get('name', 'unknown'),
                        "location": selected_device.get('location', 'unknown')
                        }



                    return {
                        "message": f"Slot {selected_device['location']} successfully booked.",
                        "booking_code": booking_code,
                        "slot_id": selected_device['ID'],
                        "type": selected_device.get('type', 'unknown'),
                        "name": selected_device.get('name', 'unknown'),
                        "location": selected_device.get('location', 'unknown')
                    }
                else:
                    return {"message": "No free slots available"}
            else:
                raise cherrypy.HTTPError(500, 'Error getting parking data')

        except requests.exceptions.RequestException as e:
            cherrypy.log(f"Request error: {str(e)}")
            raise cherrypy.HTTPError(500, 'Error during communication with the parking system')


if __name__ == '__main__':
    
    conf = {
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'tools.sessions.on': True,
        'tools.response_headers.on': True,
        'tools.response_headers.headers': [('Content-Type', 'application/json')]
    }
}
    settings = json.load(open(SETTINGS))
    service_port = int(settings["serviceInfo"]["port"])
    res = ReservationService(settings)
    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': service_port})
    cherrypy.tree.mount(res, '/', conf)
    try:
        cherrypy.engine.start()
        cherrypy.quickstart(res)
        print(f"Reservation service started on port {service_port}.")
        cherrypy.engine.block()
    except KeyboardInterrupt:
        print("Shutting down Reservation service...")
    finally:
        res.stop()
        cherrypy.engine.exit()