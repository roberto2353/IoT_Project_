import datetime
import json
from collections import defaultdict
import os
import random
import shutil
import time
import cherrypy
import pytz
import requests
from MyMQTT import MyMQTT
import threading
import uuid
from pathlib import Path
from threading import Lock
import os


P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class Algorithm:
    def __init__(self, devices, baseTopic, broker, port):
        conf = json.load(open(SETTINGS))
        self.catalog_url = conf["catalog_url"]
        #self.adaptor_url = conf["adaptor_url"]
        self.needed_services = conf["needed_services"]
        self.ports = self.request_to_catalog()
        self.exit_url = f'http://exit:{self.ports["ExitService"]}'
        print(self.exit_url)
        self.setting_status_path = P / 'settings_status.json'
        self.pubTopic = f"{baseTopic}"
        self.client = MyMQTT(clientID="Simulation_F", broker=broker, port=port, notifier=None)
        self.messageBroker = broker
        self.port = port
        self.devices = devices
        self.n_floors = 0
        self.n_tot_dev = 0
        self.n_dev_per_floor = []
        self.n_occ_dev_per_floor = []
        self.floors = []
        self.tot_occupied = 0
        self.arrivals = []
        self.t_hold_time = 120 # 15 min
        
        self.lock = Lock()  # Create a lock

    def request_to_catalog(self):
        try:
            response = requests.get(f"{self.catalog_url}/services")
            response.raise_for_status()
            resp = response.json()
            services = resp.get("services", [])
            ports = {service["name"]: int(service["port"])
                    for service in services 
                    if service["name"] in self.needed_services}

            print(ports)
            return ports
        except requests.exceptions.RequestException as e:
            raise cherrypy.HTTPError(500, f"Error communicating with catalog: {str(e)}")
        
    def start(self):
        """Start the MQTT client."""
        self.client.start()  # Start MQTT client connection
        print(f"Publisher connected to broker {self.messageBroker}:{self.port}")
       

    def stop(self):
        """Stop the MQTT client."""
        self.client.stop()  # Stop MQTT client connection

        # self.t_hold_time = 30

    def countFloors(self):
        self.floors=[]
        for device in self.devices:
            floor = self.extract_floor(device["deviceInfo"]['location'])
            if floor not in self.floors:
                self.floors.append(floor)
        self.n_floors = len(self.floors)
        print(f"total number of floors: {self.n_floors}")

    def countDev(self):
        self.n_tot_dev = len(self.devices)
        print(f"total parkings: {self.n_tot_dev}")

    def devPerFloorList(self):
        self.n_dev_per_floor=[]
        self.n_dev_per_floor=[]
        for floor in self.floors:
            count = sum(1 for dev in self.devices if self.extract_floor(dev["deviceInfo"]['location']) == floor)
            self.n_dev_per_floor.append(count)
            print(f"number of parking per floor {floor}: {count}")

    def occDevPerFloorList(self):
        self.n_occ_dev_per_floor=[]
        self.n_occ_dev_per_floor=[]
        for floor in self.floors:
            count = sum(1 for dev in self.devices if self.extract_floor(dev["deviceInfo"]['location']) == floor and dev["deviceInfo"]['status'] in ("occupied", "reserved"))
            self.n_occ_dev_per_floor.append(count)
            print(f"number of occupied/booked parking for floor {floor}: {count}")

    def update_device_status(self, device):
        # status already changed/updated in the received device
        with self.lock:

            with open(self.setting_status_path, 'r') as f:
                data = json.load(f)
            
            # Finds only device that as someting to be updated
            
        if device["deviceInfo"]['status'] == 'free': #departure case
            for dev in data["devices"]:
               if dev["deviceInfo"]['ID'] == device["deviceInfo"]['ID']:
                    print("\nOLD DATA TO UPDATE AFTER DEPARTURE:\n")
                    print(f'{dev["deviceInfo"]["ID"]},{dev["deviceInfo"]["status"]}, {dev["deviceInfo"]["last_update"]}, {dev["deviceInfo"]["booking_code"]}, {dev["deviceInfo"]["active"]}\n')
                    dev["deviceInfo"]['status'] = device["deviceInfo"]['status']
                    dev["deviceInfo"]['last_update'] = device["deviceInfo"]['last_update']
                    dev["deviceInfo"]['booking_code'] = ""
                    dev["deviceInfo"]['booking_code'] = ""
                    dev["deviceInfo"]['active'] = device["deviceInfo"]['active']
                    print("\n NEW DATA TO INSERT IN THE DB \n")
                    print(f'{dev["deviceInfo"]["ID"]},{dev["deviceInfo"]["status"]}, {dev["deviceInfo"]["last_update"]}, {dev["deviceInfo"]["booking_code"]}, {dev["deviceInfo"]["active"]}\n')
                    print("\nTAKEN FROM THE OLD DEV, THEN PASSED TO HANDLING DEPARTURE WITH VALUES\n")
                    print(print(f'{device["deviceInfo"]["ID"]},{device["deviceInfo"]["status"]}, {device["deviceInfo"]["last_update"]}, {device["deviceInfo"]["booking_code"]}, {device["deviceInfo"]["active"]}\n')
                )
                    break
                
            with self.lock:    
            # RRewrites data with updated values
                with open(self.setting_status_path, 'w') as f:
                    json.dump(data, f, indent=4)
            event = {
                "n": f'{device["deviceInfo"]["ID"]}/status', 
                "u": "boolean", 
                "t": str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                "v": device["deviceInfo"]['status'], 
                "sensor_id": device["deviceInfo"]['ID'],
                "location": device["deviceInfo"]['location'],
                "type": device["deviceInfo"]['type'],
                "booking_code":device["deviceInfo"]['booking_code'],
                "booking_code":device["deviceInfo"]['booking_code'],
                "fee": device["deviceInfo"]['fee'],
                "duration":device["deviceInfo"]['duration'],
                "floor": self.extract_floor(device["deviceInfo"]['location']),
                "active": device["deviceInfo"]['active'],
                "parking":'DevConnector1'
                }
        else:                          #arrival case
            for dev in data["devices"]:
                if dev["deviceInfo"]['ID'] == device["deviceInfo"]['ID']:
                    dev["deviceInfo"]['status'] = device["deviceInfo"]['status']
                    dev["deviceInfo"]['last_update'] = device["deviceInfo"]['last_update']
                    dev["deviceInfo"]['booking_code'] = device["deviceInfo"]['booking_code']
                    dev["deviceInfo"]['active'] = device["deviceInfo"]['active']
                    break  # break after finding the device
            with self.lock:
            # rewrite the JSON with updated values
                with open(self.setting_status_path, 'w') as f:
                    json.dump(data, f, indent=4)
            event = {
                "n": f'{device["deviceInfo"]["ID"]}/status', 
                "u": "boolean", 
                "t": str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                "v": device["deviceInfo"]['status'], 
                "sensor_id": device["deviceInfo"]['ID'],
                "location": device["deviceInfo"]['location'],
                "type": device["deviceInfo"]['type'],
                "booking_code": device["deviceInfo"]['booking_code'],
                "floor": self.extract_floor(device["deviceInfo"]['location']),
                "active": device["deviceInfo"]['active'],
                "parking":'DevConnector1'
                }
            
        message = {"bn": device["deviceInfo"]['name'], "e": [event]}
        mqtt_topic = f'{self.pubTopic}/{str(device["deviceInfo"]["ID"])}/status'

        # MQTT msg sent to adaptor
        self.client.myPublish(mqtt_topic, json.dumps(message))
        print(f"Messaggio pubblicato su topic {mqtt_topic}")
        
    @staticmethod
    def extract_floor(location):
        if location.startswith("P"):
            return location[1]
        return None

    def totalOccupied(self):
        self.tot_occupied = sum(1 for dev in self.devices if dev["deviceInfo"]['status'] in ("occupied", "reserved"))
        print(f"total occupied parking slots: {self.tot_occupied}")

    def arrival_time(self):
        current_hour = datetime.datetime.now().hour
        if current_hour in range(0, 6) and self.tot_occupied < self.n_tot_dev - 1: #an arrival every 7.5-15 min during 0-6
            next_arrival_time = datetime.datetime.now() + datetime.timedelta(seconds=random.randint(self.t_hold_time/2, self.t_hold_time))
            self.arrivals.append(next_arrival_time)
        elif current_hour in range(6, 24) and self.tot_occupied < self.n_tot_dev - 1: # an arrival every 2-7 min during day (6-24)
            next_arrival_time = datetime.datetime.now() + datetime.timedelta(seconds=random.randint(30, int(self.t_hold_time/2)))
            self.arrivals.append(next_arrival_time)
        self.arrivals.sort()



    def changeDevState(self, device):
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        booking_code_ = str(uuid.uuid4())
        booking_code = booking_code_[:7]
        if device["deviceInfo"]['status'] == 'free':
            device["deviceInfo"]['status'] = 'occupied'
            device["deviceInfo"]['last_update'] = str(current_time)
            device["deviceInfo"]['booking_code'] = booking_code
            self.update_device_status(device)  # Send update to adaptor
            return True
        return False

    def get_free_device_on_floor(self, floor):
        print(f"Looking for the first free slot on floor {floor}:")
        for device in self.devices:
            print(f'{device["deviceInfo"]["status"]},{floor} = {self.extract_floor(device["deviceInfo"]["location"])}')
            if device["deviceInfo"]["status"] == 'free' and int(self.extract_floor(device["deviceInfo"]["location"])) == int(floor):
                print("device found")
                return device
        return None

    def routeArrivals(self, get='False'):
        print("trying to route arrivals if present...\n")
        time = datetime.datetime.now()
        if self.arrivals and time >= self.arrivals[0] and get == 'False' and self.tot_occupied < self.n_tot_dev:
            self.arrivals.pop(0)
            for floor in range(self.n_floors):
                print(f"current floor:{floor}")
                print(f"Occupied slots on this floor:{self.n_occ_dev_per_floor[floor]}; thold of occupied slots:{int(0.8 * self.n_dev_per_floor[floor])}")
                if self.n_occ_dev_per_floor[floor] < int(0.8 * self.n_dev_per_floor[floor]):
                    device = self.get_free_device_on_floor(floor)
                    if device and self.changeDevState(device):
                        print(f'Device {device["deviceInfo"]["ID"]} has changed state to {device["deviceInfo"]["status"]}')
                        return device
            # case above 80%
            print("All floor are 80perc occupied...")
            device = next((d for d in self.devices if d["deviceInfo"]['status'] == 'free'), None)
            if device and self.changeDevState(device):
                    print("80 percent of parking from all floors are occupied, returned if possible first free parking.")
                    print(f'Device {device["deviceInfo"]["ID"]} has changed state to {device["deviceInfo"]["status"]}')
                    if device:
                        print(f'Parking found, parking = {device["deviceInfo"]["location"]}')
                        return device
            else:
                print("No free parking found")
                return None
                
                
        if get == 'True':
            for floor in range(self.n_floors):
                if self.n_occ_dev_per_floor[floor] < int(0.8 * self.n_dev_per_floor[floor]):
                    device = self.get_free_device_on_floor(floor)
                    if device and device["deviceInfo"]['status'] == 'free':
                        print("device found for the registration in route arrivals")
                        return {"message": "Parking found", "parking": device}
                    

            device = next((d for d in self.devices if d["deviceInfo"]['status'] == 'free'), None)
            if device:
                return {"message": "Parking found", "parking": device}
            return {"message": "No free parking found"}
        
    def handle_departures(self):
        departure_probability = 0.1  # 10% chance for any parked car to leave
        time = datetime.datetime.now()
        current_hour = time.hour
        threshold = 0 #min
        if current_hour in range(0, 6):
            threshold = 60
        else:
            threshold = 30
        for device in self.devices:
            print("booking_code: ", device['deviceInfo']['booking_code'])
            if (device["deviceInfo"]['status'] == 'occupied' and device["deviceInfo"]["active"] in ['True', True] and len(device["deviceInfo"]["booking_code"]) >= 7):
                if random.random() < departure_probability and (time - datetime.datetime.strptime(device["deviceInfo"]["last_update"], "%Y-%m-%d %H:%M:%S"))>= datetime.timedelta(minutes=threshold):
                    print(f"handling departures of cars altready parked for more than {threshold} min...")
                    print(f'found device to depart has {device["deviceInfo"]["status"], device["deviceInfo"]["active"], device["deviceInfo"]["booking_code"]}')
                    exit_url = f'{self.exit_url}/calcola_fee'
                    headers = {'Content-Type': 'application/json'}

                    reservation_data = {
                        "sensor_id": device["deviceInfo"]["ID"]
                        }

                    try:
                        
                        req = requests.post(exit_url, headers=headers, json=reservation_data)
                        # Only proceed if the response status code is 200 (OK)
                        if req.status_code == 200:
                            try:
                                response_data = req.json()  # Attempt to parse response as JSON
                                print(f"Response JSON: {response_data}")

                                # Ensure required keys exist in the response data
                                if 'parking_fee' in response_data and 'parking_duration' in response_data:
                                    # Update device information
                                    device["deviceInfo"]['status'] = "free"
                                    device["deviceInfo"]['last_update'] = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                                    device["deviceInfo"]['fee'] = str(response_data['parking_fee'])
                                    device["deviceInfo"]['duration'] = str(response_data['parking_duration'])
                                    #device["deviceInfo"]['booking_code'] = ""
                                    #device["deviceInfo"]['booking_code'] = ""
                            
                                    # Send updated status to adaptor
                                    self.update_device_status(device)
                                    print(f'Device {device["deviceInfo"]["ID"]} at {device["deviceInfo"]["location"]} is now free. Car has departed.')
                                else:
                                    print("Error: Response data missing 'parking_fee' or 'parking_duration'.")
                            except ValueError:
                                print("Error: Response is not in JSON format.")
                        else:
                            print(f"Error: Request failed with status code {req.status_code}")
                    except requests.exceptions.RequestException as e:
                        print(f"Request error: {e}")
                    

    def refreshDevices(self):
        if not self.setting_status_path.exists():
            return
        else:
            conf = json.load(open(self.setting_status_path))
            self.devices = conf['devices']
    
    def free_all_parking_on_dbs(self):
        try:
            with self.lock:
                with open(self.setting_status_path, 'r') as f:
                    data = json.load(f)
                print("FREE STATUS SET ON DBs\n")
            
        except json.JSONDecodeError:
            print("Error: setting_status.json is corrupted or empty.")
            
            
        for device in data["devices"]:
            event = {
                "n": f'{device["deviceInfo"]["ID"]}/status', 
                "u": "boolean", 
                "t": str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                "v": "free", 
                "sensor_id": device["deviceInfo"]['ID'],
                "location": device["deviceInfo"]['location'],
                "type": device["deviceInfo"]['type'],
                "booking_code": device["deviceInfo"]['booking_code'],
                "floor": self.extract_floor(device["deviceInfo"]['location']),
                "active": device["deviceInfo"]['active'],
                "parking":'DevConnector1',
                "flag":True
                }
            message = {"bn": device["deviceInfo"]['name'], "e": [event]}
            mqtt_topic = f'{self.pubTopic}/{str(device["deviceInfo"]["ID"])}/status'
            self.client.myPublish(mqtt_topic, json.dumps(message))
            print(f"Message published on topic {mqtt_topic}")
            
    def intraloop_update_var(self):
        print("refreshing devices...\n")
        self.refreshDevices()
        self.countFloors()
        self.countDev()
        self.devPerFloorList()
        self.occDevPerFloorList()
        self.totalOccupied()

    def simulate_arrivals_loop(self):
        while True:
            
            print("Loop start:\n")
            self.intraloop_update_var()
            self.handle_departures()
            self.intraloop_update_var()
            self.arrival_time()
            self.routeArrivals()
            time.sleep(60)


class EntranceAlgorithmService:
    def __init__(self):
        self.lock = Lock()
        with self.lock:
            try:
                conf = json.load(open(SETTINGS))
            except json.JSONDecodeError:
                print("Error: settings.json is corrupted or empty.")
        devices = conf['devices']
        baseTopic = conf["baseTopic"]
        broker = conf["messageBroker"]
        port = conf["brokerPort"]
        #catalog_url = conf["catalog_url"]
        #adaptor_url = conf["adaptor_url"]
        self.setting_status_path = P / 'settings_status.json'
        self.reset_file(self.setting_status_path)
        
        # I think it's better to delete it and create it again each time, 
        # in case the devices in settings change, otherwise now they are not updated
        # Check if setting_status.json exists, and create it if it doesn't
        self.ensure_setting_status(devices)
        try:
            with self.lock:
                with open(self.setting_status_path, 'r') as f:
                    conf = json.load(f)
                devices = conf.get('devices', [])
                print("Check SETTING_STATUS initialization:\n"+ f"{devices}")
            
        except json.JSONDecodeError:
            print("Error: setting_status.json is corrupted or empty.")
        self.algorithm = Algorithm(devices, baseTopic, broker, port)  # Create Algorithm instance
    
    def reset_file(self, filepath):
        try:
            os.remove(filepath)
            print(f"File {filepath} deleted successfully.")
        except FileNotFoundError:
            print(f"File {filepath} not found.")
        except Exception as e:
            print(f"Error deleting file {filepath}: {e}")
        
    def ensure_setting_status(self, devices):
    
        if not self.setting_status_path.exists() or os.path.getsize(self.setting_status_path) == 0:
        # Load the original settings JSON from the SETTINGS path
            with self.lock:
                with open(SETTINGS, 'r') as settings_file:
                    sett_json = json.load(settings_file)
                    devices_data = sett_json.get('devices', [])

        # Add/update each device with last_update, booking_code, and status
            current_time = time.time()  # Unix time in seconds
            for device in devices_data:
                device["deviceInfo"]["status"] = "free"
                device["deviceInfo"]["booking_code"] = ""
                device["deviceInfo"]["last_update"] = current_time
            with self.lock:
        # Save the modified data to setting_status.json
                with open(self.setting_status_path, 'w') as f:
                    json.dump({"devices": devices_data}, f, indent=4)

            print("setting_status.json created with updated device information.")
        else:
            print("setting_status.json already exists.")
    
        
    

    def sim_loop_start(self):
        threading.Thread(target=self.algorithm.simulate_arrivals_loop, daemon=True).start()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_best_parking(self):
        # Assuming get_devices is a method of the Algorithm class
        return self.algorithm.routeArrivals(get='True')
    


if __name__ == '__main__':
    
    entranceAlgorithmService = EntranceAlgorithmService()
    entranceAlgorithmService.algorithm.start()
    entranceAlgorithmService.algorithm.free_all_parking_on_dbs()
    entranceAlgorithmService.sim_loop_start()
    #cherrypy.config.update({'server.socket_port': 8081})  # Change to a different port
    #cherrypy.quickstart(entranceAlgorithmService)
    