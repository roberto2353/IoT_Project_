import datetime
import json
from collections import defaultdict
import os
import random
import time
import cherrypy
import requests
from MyMQTT import MyMQTT
import threading
import uuid
from pathlib import Path

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class Algorithm:
    def __init__(self, devices, baseTopic, broker, port):
        self.pubTopic = f"{baseTopic}"
        self.client = MyMQTT(clientID="Simulation", broker=broker, port=port, notifier=None)
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
        self.t_hold_time = 15

    def start(self):
        """Start the MQTT client."""
        self.client.start()  # Start MQTT client connection
        print(f"Publisher connesso al broker {self.messageBroker}:{self.port}")

    def stop(self):
        """Stop the MQTT client."""
        self.client.stop()  # Stop MQTT client connection


    def countFloors(self):
        self.floors=[]
        for device in self.devices:
            floor = self.extract_floor(device['location'])
            if floor not in self.floors:
                self.floors.append(floor)
        self.n_floors = len(self.floors)
        print(f"total number of floors: {self.n_floors}")

    def countDev(self):
        self.n_tot_dev = len(self.devices)
        print(f"total parkings: {self.n_tot_dev}")

    def devPerFloorList(self):
        self.n_dev_per_floor=[]
        for floor in self.floors:
            count = sum(1 for dev in self.devices if self.extract_floor(dev['location']) == floor)
            self.n_dev_per_floor.append(count)
            print(f"number of parking per floor {floor}: {count}")

    def occDevPerFloorList(self):
        self.n_occ_dev_per_floor=[]
        for floor in self.floors:
            count = sum(1 for dev in self.devices if self.extract_floor(dev['location']) == floor and dev['status'] in ("occupied", "reserved"))
            self.n_occ_dev_per_floor.append(count)
            print(f"number of occupied/booked parking for floor {floor}: {count}")

    def update_device_status(self, device):
        
        event = {
                "n": f"{device['ID']}/status", 
                "u": "boolean", 
                "t": str(datetime.datetime.now()), 
                "v": device['status'],  # Cambiamo lo stato in 'occupied'
                "sensor_id": device['ID'],
                "location": device['location'],
                "type": device['type'],
                "booking_code": device['booking_code']
            }
        message = {"bn": device['name'], "e": [event]}
        mqtt_topic = f"{self.pubTopic}/{device['ID']}/status"

        # Invio del messaggio MQTT all'adaptor
        self.client.myPublish(mqtt_topic, json.dumps(message))
        print(f"Messaggio pubblicato su topic {mqtt_topic}")

        # Risposta di successo al frontend
        return {
                "message": f"Slot {device['location']} has been successfully  occupied.",
                "slot_id": device['ID']
            }




    @staticmethod
    def extract_floor(location):
        if location.startswith("P"):
            # print(f"{location[1]}")
            return location[1]
        return None

    def totalOccupied(self):
        self.tot_occupied = sum(1 for dev in self.devices if dev['status'] in ("occupied", "reserved"))
        print(f"total occupied parking slots: {self.tot_occupied}")

    def arrival_time(self):
        current_hour = datetime.datetime.now().hour
        if current_hour in range(0, 6) and self.tot_occupied < self.n_tot_dev:
            next_arrival_time = datetime.datetime.now() + datetime.timedelta(seconds=random.randint(0, self.t_hold_time))
            self.arrivals.append(next_arrival_time)
        elif current_hour in range(6, 24) and self.tot_occupied < self.n_tot_dev:
            next_arrival_time = datetime.datetime.now() + datetime.timedelta(seconds=random.randint(0, int(self.t_hold_time/2)))
            self.arrivals.append(next_arrival_time)
        self.arrivals.sort()


    def changeDevState(self, device, floor, time):
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        booking_code_ = str(uuid.uuid4())
        booking_code = booking_code[:6]
        if device['status'] == 'free' and int(self.extract_floor(device['location'])) == int(floor):
            device['status'] = 'occupied'
            device['last_update'] = str(current_time)
            device['booking_code'] = booking_code
            self.update_device_status(device)  # Send update to adaptor
            return True
        return False

    def get_free_device_on_floor(self, floor):
        for device in self.devices:
            print(f"{device['status']},{floor}")
            print(f"{self.extract_floor(device['location'])}")
            if device['status'] == 'free' and int(self.extract_floor(device['location'])) == int(floor):
                print("device found")
                return device
        return None

    def routeArrivals(self, get='False'):
        flag = 0
        time = datetime.datetime.now()
        if self.arrivals and time >= self.arrivals[0] and get == 'False':
            print()
            self.arrivals.pop(0)
            for floor in range(self.n_floors):
                print(f"current floor:{floor}")
                print(f"posti occupati per piano prova:{self.n_occ_dev_per_floor}")
                print(f"posti occupati:{self.n_occ_dev_per_floor[floor]}; thold posti occupati:{int(0.8 * self.n_dev_per_floor[floor])}")
                if self.n_occ_dev_per_floor[floor] < int(0.8 * self.n_dev_per_floor[floor]):
                    device = self.get_free_device_on_floor(floor)
                    if device and self.changeDevState(device, floor, time):
                        print(f"Device {device['ID']} has changed state to {device['status']}")
                        flag=1
                        return device

            if flag == 0:
                device = next((d for d in self.devices if d['status'] == 'free'), None)
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if device and self.changeDevState(device, floor, time):
                    print("80 percent of parking from all floors are occupied, returned if possible first free parking.")
                    print(f"Device {device['ID']} has changed state to {device['status']}")
                    flag=1
                    return device
        if get == 'True':
            for floor in range(self.n_floors):
                if self.n_occ_dev_per_floor[floor] < int(0.8 * self.n_dev_per_floor[floor]):
                    device = self.get_free_device_on_floor(floor)
                    if device and device['status'] == 'free':
                        flag=1
                        print("device found for the registration in route arrivals")
                        return {"message": "Parking found", "parking": device}
                    

            if flag == 0:
                device = next((d for d in self.devices if d['status'] == 'free'), None)
                if device:
                    return {"message": "Parking found", "parking": device}
                return {"message": "No free parking found"}
            
            
    def handle_departures(self):
        departure_probability = 0.1  # 10% chance for any parked car to leave
        current_time = datetime.datetime.now()

        for device in self.devices:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if device['status'] == 'occupied':
                if random.random() < departure_probability:
                    device['status'] = 'free'
                    device['last_update'] = str(current_time)
                    device['booking_code'] = ""
                    self.update_device_status(device)  # Send update to adaptor
                    print(f"Device {device['ID']} at {device['location']} is now free. Car has departed.")
                    #TODO: ONLY REGISTERED USERS AND RANDOM USERS WILL DEPARTURE WITH THIS METHOD. 
                    # NON REGISTERED USERS BUT USERS THAT MADE A RESERVATION REQUEST WILL BE HANDLED BY EXIT FILE.

    def refreshDevices(self):
        adaptor_url = 'http://127.0.0.1:5000/'  # URL for adaptor
        response = requests.get(adaptor_url)
        response.raise_for_status()  # Check if response is correct
        self.devices = response.json()

    def simulate_arrivals_loop(self):
        while True:
            
            self.refreshDevices()
            self.countFloors()
            self.countDev()
            self.devPerFloorList()
            self.occDevPerFloorList()
            self.totalOccupied()
            self.arrival_time()
            self.handle_departures()
            self.routeArrivals()
            time.sleep(5)


class EntranceAlgorithmService:
    def __init__(self):
        adaptor_url = 'http://127.0.0.1:5000/'  # URL for adaptor
        response = requests.get(adaptor_url)
        response.raise_for_status()  # Check if response is correct
        devices = response.json()  # Fetch devices from adaptor
        conf = json.load(open(SETTINGS))
        baseTopic = conf["baseTopic"]
        broker = conf["messageBroker"]
        port = conf["brokerPort"]
        catalog_url = conf["catalog_url"]
        self.algorithm = Algorithm(devices,baseTopic, broker, port)  # Create Algorithm instance

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
    entranceAlgorithmService.sim_loop_start()
    cherrypy.config.update({'server.socket_port': 8081})  # Change to a different port
    cherrypy.quickstart(entranceAlgorithmService)