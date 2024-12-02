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
        self.setting_status_path = P / 'settings_status.json'
        self.pubTopic = f"{baseTopic}"
        self.client = MyMQTT(clientID="Simulation2_F", broker=broker, port=port, notifier=None)
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
        self.t_hold_time = 900 # min
        
        self.lock = Lock()  # Create a lock

    def start(self):
        """Start the MQTT client."""
        self.client.start()  # Start MQTT client connection
        print(f"Publisher connesso al broker {self.messageBroker}:{self.port}")
       

    def stop(self):
        """Stop the MQTT client."""
        self.client.stop()  # Stop MQTT client connection

        # self.t_hold_time = 15

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
            # Leggi i dati esistenti dal file
            with open(self.setting_status_path, 'r') as f:
                data = json.load(f)
            
            # Cerca e aggiorna solo il dispositivo in considerazione
            
        if device["deviceInfo"]['status'] == 'free': #departure case
            for dev in data["devices"]:
                if dev["deviceInfo"]['ID'] == device["deviceInfo"]['ID']:
                    print("\nDATI VECCHI DA AGGIORNARE DOPO LA PARTENZA:\n")
                    print(f'{dev["deviceInfo"]["ID"]},{dev["deviceInfo"]["status"]}, {dev["deviceInfo"]["last_update"]}, {dev["deviceInfo"]["booking_code"]}, {dev["deviceInfo"]["active"]}\n')
                    dev["deviceInfo"]['status'] = device["deviceInfo"]['status']
                    dev["deviceInfo"]['last_update'] = device["deviceInfo"]['last_update']
                    dev["deviceInfo"]['booking_code'] = ""
                    dev["deviceInfo"]['active'] = device["deviceInfo"]['active']
                    print("\n NUOVI DATI DA INSERIRE NEL DB \n")
                    print(f'{dev["deviceInfo"]["ID"]},{dev["deviceInfo"]["status"]}, {dev["deviceInfo"]["last_update"]}, {dev["deviceInfo"]["booking_code"]}, {dev["deviceInfo"]["active"]}\n')
                    print("\n PRESI DAL DEVICE PASSATO AD HANDLING DEPARTURE CON VALORI\n")
                    print(print(f'{device["deviceInfo"]["ID"]},{device["deviceInfo"]["status"]}, {device["deviceInfo"]["last_update"]}, {device["deviceInfo"]["booking_code"]}, {device["deviceInfo"]["active"]}\n')
                )
                    break
                
            with self.lock:    
            # Riscrivi il file con i dati aggiornati
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
                "fee": device["deviceInfo"]['fee'],
                "duration":device["deviceInfo"]['duration'],
                "floor": self.extract_floor(device["deviceInfo"]['location']),
                "active": device["deviceInfo"]['active'],
                "parking":'DevConnector2'
                }
        else:                          #arrival case
            for dev in data["devices"]:
                if dev["deviceInfo"]['ID'] == device["deviceInfo"]['ID']:
                    dev["deviceInfo"]['status'] = device["deviceInfo"]['status']
                    dev["deviceInfo"]['last_update'] = device["deviceInfo"]['last_update']
                    dev["deviceInfo"]['booking_code'] = device["deviceInfo"]['booking_code']
                    dev["deviceInfo"]['active'] = device["deviceInfo"]['active']
                    break  # Esce dopo aver trovato il dispositivo
            with self.lock:
            # Riscrivi il file con i dati aggiornati
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
                "parking":'DevConnector2'
                }
            
        message = {"bn": device["deviceInfo"]['name'], "e": [event]}
        mqtt_topic = f'{self.pubTopic}/{str(device["deviceInfo"]["ID"])}/status'

        # Invio del messaggio MQTT all'adaptor
        self.client.myPublish(mqtt_topic, json.dumps(message))
        print(f"Messaggio pubblicato su topic {mqtt_topic}")

        # Risposta di successo al frontend
        # return {
        #         "message": f"Slot {device['location']} has been successfully  occupied.",
        #         "slot_id": device['ID']
        #     }

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
        elif current_hour in range(6, 24) and self.tot_occupied < self.n_tot_dev - 1: # an arrival every 1-3.75 min during day (6-24)
            next_arrival_time = datetime.datetime.now() + datetime.timedelta(seconds=random.randint(60, int(self.t_hold_time/4)))
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
        if self.arrivals and time >= self.arrivals[0] and get == 'False':
            self.arrivals.pop(0)
            for floor in range(self.n_floors):
                print(f"current floor:{floor}")
                print(f"posti occupati per piano prova:{self.n_occ_dev_per_floor}")
                print(f"posti occupati:{self.n_occ_dev_per_floor[floor]}; thold posti occupati:{int(0.8 * self.n_dev_per_floor[floor])}")
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
     
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def fee_and_duration_calc(self,device):
        booking_start_time_str = device.get('time', None)
        booking_start_time = datetime.datetime.strptime(booking_start_time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)

            
        #booking_start_timestamp = int(booking_start_time.timestamp())

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        current_time_ok = datetime.datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
            
        # print("current_time: ", current_time_ok, "booking_start_time: " ,booking_start_time)
        parking_duration_seconds = (current_time_ok - booking_start_time).total_seconds()
        parking_duration_hours = parking_duration_seconds / 3600 # Converti i secondi in ore
        parking_duration_mins = parking_duration_seconds / 60 # Converti i secondi in min

        # print("parking_duration_hours :", parking_duration_hours)

        if parking_duration_hours <= 10:
            fee = parking_duration_hours * 2  # 2 euro per ora
            return fee, parking_duration_mins
        else:
            # Se supera le 10 ore, calcola 20 euro ogni 24 ore (giorno intero)
            full_days = int(parking_duration_hours // 24)  # Numero di giorni interi
            remaining_hours = parking_duration_hours % 24  # Ore rimanenti dopo giorni interi
            fee = full_days * 20 + (remaining_hours * 2 if remaining_hours <= 10 else 20)
            return fee, parking_duration_mins
        
        
        
        
                
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
            #print(f" last update:{device['last_update']}")
            if (device["deviceInfo"]['status'] == 'occupied' and device["deviceInfo"]["active"] in ['True', True] and len(device["deviceInfo"]["booking_code"]) > 6):
                if random.random() < departure_probability and (time - datetime.datetime.strptime(device["deviceInfo"]["last_update"], "%Y-%m-%d %H:%M:%S"))>= datetime.timedelta(minutes=threshold):
                    print(f"handling departures of cars altready parked for more than {threshold} min...")
                    print(f'found device to depart has {device["deviceInfo"]["status"], device["deviceInfo"]["active"], device["deviceInfo"]["booking_code"]}')
                    reservation_url = 'http://127.0.0.1:8056/calcola_fee'
                    headers = {'Content-Type': 'application/json'}

                    reservation_data = {
                        "sensor_id": device["deviceInfo"]["ID"]
                        }

                    try:
                        
                        req = requests.post(reservation_url, headers=headers, json=reservation_data)
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
                    
                    #TODO: ONLY REGISTERED USERS AND RANDOM USERS WILL DEPARTURE WITH THIS METHOD. 
                    # NON REGISTERED USERS BUT USERS THAT MADE A RESERVATION REQUEST WILL BE HANDLED BY EXIT FILE.

    def refreshDevices(self):
        # adaptor_url = 'http://127.0.0.1:5001/'  # URL for adaptor
        # response = requests.get(adaptor_url)
        # response.raise_for_status()  # Check if response is correct
        # self.devices = response.json()
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
                "parking":'DevConnector2',
                "flag":True
                }
            message = {"bn": device["deviceInfo"]['name'], "e": [event]}
            mqtt_topic = f'{self.pubTopic}/{str(device["deviceInfo"]["ID"])}/status'
            self.client.myPublish(mqtt_topic, json.dumps(message))
            print(f"Messaggio pubblicato su topic {mqtt_topic}")
            
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
            
            print("inizio loop:\n")
            self.intraloop_update_var()
            self.handle_departures()
            self.intraloop_update_var()
            self.arrival_time()
            self.routeArrivals()
            time.sleep(60)


class EntranceAlgorithmService:
    def __init__(self):
        adaptor_url = 'http://127.0.0.1:5001/'  # URL for adaptor
        # response = requests.get(adaptor_url)
        # response.raise_for_status()  # Check if response is correct
        # devices = response.json()  # Fetch devices from adaptor
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
        catalog_url = conf["catalog_url"]
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
                print("CONTROLLO INIZIALIZZAZIONE SETTING_STATUS:\n"+ f"{devices}")
            
        except json.JSONDecodeError:
            print("Error: setting_status.json is corrupted or empty.")
        self.algorithm = Algorithm(devices,baseTopic, broker, port)  # Create Algorithm instance
    
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
    cherrypy.config.update({'server.socket_port': 8092})  # Change to a different port
    cherrypy.quickstart(entranceAlgorithmService)
    