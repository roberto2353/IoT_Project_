import json
import threading
import time
import cherrypy
import requests
from pathlib import Path
import paho.mqtt.client as PahoMQTT
from datetime import datetime
import sys


P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class SlotBoard:
    """Shows with tab the free and occupied spots"""
    def __init__(self, settings):
        self.free_slots = 0
        self.occupied_slots = 0
        self.total_slots = 0
        self.sensors_data = {}
        self.catalogUrl = settings["catalog_url"]
        self.deviceInfo = settings["deviceInfo"]
        self.needed_services = settings["needed_services"]
        self.lock = threading.Lock()
        self.initialize_board()
        
    def initialize_board(self):
        
        try:
            
            parking_url = self.catalogUrl+"/parkings"
            response = requests.get(parking_url)
            response.raise_for_status()
            parkings = response.json().get("parkings", [])

            print("Parkings available:")
            for idx, parking in enumerate(parkings):
                print(f"{idx + 1}. Name: {parking['name']}, Address: {parking['url']}, Port: {parking['port']}")

            # Ask the user to choose the parking
            choice = int(input("Select number of parking to use: ")) - 1
            if choice < 0 or choice >= len(parkings):
                print("Not valid. Try again")
                return

            selected_parking = parkings[choice]
            devConnUrl = f"http://{selected_parking['url']}:{selected_parking['port']}/devices"
            print(f"Connecting to parking: {selected_parking['name']}")

            #Register tab in catalog
            self.activate_tab(selected_parking)
            self.register_device()

            # Get the devices of selected parking
            response = requests.get(devConnUrl)
            response.raise_for_status()  
            devices = response.json()
            print(f"Devices in parking {selected_parking['name']}: {devices}")
            
        
            # Get the list of devices from the adaptor
            slots = response.json()
            if isinstance(slots, str): 
                final_data = json.loads(slots)
                print("Double-encoded JSON:", final_data)
            unique_ids = {device["deviceInfo"]["ID"] for device in final_data["devices"]}
            self.total_slots = len(unique_ids)
            print(f"Tab initialized: {self.total_slots} total spots")

            devices = final_data["devices"]
            for slot in devices:
                slot_id = slot["deviceInfo"]["ID"]
                status = slot["deviceInfo"]["status"]
                self.sensors_data[slot_id] = status
                
                print(f"Initialization of slot {slot_id} with status: {status}")
                
                if status == "free":
                    self.free_slots += 1
                elif status == "occupied":
                    self.occupied_slots += 1

            # Initial state of tab
            self.display_board()

        except Exception as e:
            print(f"Error in tab initialization: {e}")

    def activate_tab(self, selected_parking):
        
        self.deviceInfo["active"] = True
        self.deviceInfo["location"] = selected_parking["name"]
        self.write_json()

    def write_json(self):
        try:
            with self.lock:
                with open(SETTINGS, 'r') as settings:
                    data = json.load(settings)
                data['deviceInfo'] = self.deviceInfo

                with open(SETTINGS, 'w') as settings:
                    json.dump(data, settings, indent=4)
                
                
            
        except FileNotFoundError:
            print("Settings file not found.")
        except json.JSONDecodeError:
            print("Error decoding JSON from the settings file.")
        
    def register_device(self):
        url = f"{self.catalogUrl}/devices"
        response = requests.post(url, json=self.deviceInfo)
        if response.status_code == 200:
            
            print(f"Device Tab registered successfully.")
        else:
            print(f"Failed to register device: {response.status_code} - {response.text}")

    def update_slot(self, slot_id, status):
        """Updates free and occupied spots count"""
        
        print(f"Update of slot {slot_id}: New state ={status}")
        

        if status == "free":
            self.occupied_slots -= 1
            self.free_slots += 1

        elif status == "occupied":
            self.free_slots -= 1
            self.occupied_slots += 1


        print(f"Updated free slots: {self.free_slots}, Updated occupied slots: {self.occupied_slots}")
        self.display_board()



    def display_board(self):
        """Displays live tab status"""
        print(f"Free slots: {self.free_slots} | Occupied slots: {self.occupied_slots} | Total: {self.total_slots}")

class MySubscriber:

    def __init__(self, clientID, settings, message_callback):
        self.clientID = clientID
        self.serviceInfo = settings["serviceInfo"]
        self.serviceID = self.serviceInfo["ID"]
        self.catalog_address = settings["catalog_url"]
        self.topic = settings["sensorTopic"]
        self.deviceInfo = settings["deviceInfo"]
        self.aliveTopic = settings["aliveTopic"]
        self.publish_topic = f"{self.aliveTopic}{self.serviceID}"
        self.update_interval = settings["updateInterval"]  # Interval for periodic updates
        self.register_service()
        self.message_callback = message_callback
        self._paho_mqtt = PahoMQTT.Client(client_id=self.clientID)
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived
        self.messageBroker = settings["messageBroker"]
        self.port = settings["brokerPort"]
        self.qos = settings["qos"]
        self.pingInterval = settings["pingInterval"]
        self.start()
        self.pingCatalog()

    def start(self):
        """Start the subscriber and publisher."""
        self._paho_mqtt.connect(self.messageBroker, self.port)
        self._paho_mqtt.loop_start()
        self._paho_mqtt.subscribe(self.topic, self.qos)
        print(f"Subscribed to topic: {self.topic}")

        self.start_periodic_updates()  

    def stop(self):
        """Stop the subscriber and publisher."""
        self._paho_mqtt.unsubscribe(self.topic)
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

    def myOnConnect(self, client, userdata, flags, rc, properties=None):
        print(f"Connected to {self.messageBroker} with result code: {rc}")
        if rc == 0:
            print("Subscribing to topic...")
            self._paho_mqtt.subscribe(self.topic, self.qos)
        else:
            print("Connection failed!")

    def myOnMessageReceived(self, client, userdata, msg):
        print(f"Message received: Topic={msg.topic}, Payload={msg.payload.decode()}")
        self.message_callback(msg)

    def publish_message(self, message):
        """Publish a message to the MQTT broker on the specified topic."""
        try:
            self._paho_mqtt.publish(self.publish_topic, json.dumps(message))
            print(f"Published message to {self.publish_topic}: {message}")
        except Exception as e:
            print(f"Error publishing message: {e}")

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

    def pingCatalog(self):
        time.sleep(5)
        while True:
                with open(SETTINGS, 'r') as settings:
                    data = json.load(settings)
                
                    if data["deviceInfo"]["active"] == True:
                        location = data["deviceInfo"]["location"]
                        message = {
                        "bn": "updateCatalogSlot",  
                        "e": [
                        {
                            "n": f'{data["deviceInfo"]["ID"]}',  
                            "u": "IP",  
                            "t": str(time.time()), 
                            "v": ""  
                        }
                        ]
                        }
                        
                        self._paho_mqtt.publish(f'{self.aliveTopic}{data["deviceInfo"]["ID"]}', json.dumps(message))
                        print(f'Published to topic {self.aliveTopic}{data["deviceInfo"]["ID"]}: {json.dumps(message)}')
                print(f"Sensor's update terminated. Next update in {self.pingInterval} seconds")
                time.sleep(self.pingInterval)

    def start_periodic_updates(self):
        """Starts a background thread for periodic updates."""
        def periodic_update():
            time.sleep(10)
            while True:
                try:
                    message = {
                        "bn": "updateCatalogService",  
                        "e": [
                            {
                                "n": self.serviceID,  
                                "u": "IP",
                                "t": str(time.time()), 
                                "v": ""
                            }
                        ]
                    }
                    self.publish_message(message)
                    time.sleep(self.update_interval)
                except Exception as e:
                    print(f"Error during periodic update: {e}")

        # Start periodic updates in a background thread
        update_thread = threading.Thread(target=periodic_update, daemon=True)
        update_thread.start()
 

def main():
    settings = json.load(open(SETTINGS))
    slot_board = SlotBoard(settings)

    def recursive_json_decode(data):
        while isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                break
        return data

    def on_message_received(msg):
        """Callback for MQTT received messages"""
        print(f"Received message: Topic={msg.topic}, Payload={msg.payload.decode()}")

        try:
            decoded_message = msg.payload.decode()
            print(f"Decoded message (first decode): {decoded_message}")

            data = recursive_json_decode(decoded_message)
            print(f"Final decoded message: {data}")
            print(f"Data type after final decode: {type(data)}")
            print(f"Payload {data}")
            event = data.get("e", [])[0]
            slot_status = event.get("v")
            slot_id = event.get("n").split("/")[0] 

            previous_status = slot_board.sensors_data.get(slot_id, "unknown")
            
            current_time = datetime.now()  
            last_change_time = slot_board.sensors_data.get(slot_id + "_time", current_time)
            duration = (current_time - last_change_time).total_seconds() if last_change_time else 0
            
            # Update tab status
            slot_board.update_slot(slot_id, slot_status)
            slot_board.sensors_data[slot_id + "_time"] = current_time
            
        except Exception as e:
            print(f"Error in processing the message: {e}")

    subscriber = MySubscriber("SlotTabSubscriber", settings, on_message_received)
    subscriber.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        subscriber.stop()

if __name__ == '__main__':
    main()