import datetime
import json
from collections import defaultdict
import os
import random
import time

"""{
            "ID": 1,
            "name": "sensor1",
            "type": "photocell",
            "location": "P0-1",
            "commands": [
                "status"
            ],
            "last_update": 1726583952.943517,
            "status": "free",
            "booking_code": "31041555-9fba-4361-8196-5ad025de34a2"
        }"""
"""[class dev:
    def __init__(self,id,name,type,location,commands,last_update,status,booking_code):
        self.id = id
        self.name = name
        self.type = type
        self.location = location
        self.commands = commands
        self.last_update = last_update
        self.status = status
        self.booking_code = booking_code]"""

class Algorithm:
    def __init__(self, devices):
        self.devices = devices
        self.n_floors = 0
        self.n_tot_dev = 0
        self.n_dev_per_floor = []
        self.n_occ_dev_per_floor = []
        self.floors = []
        self.tot_occupied = 0
        self.arrivals = []
        self.t_hold_time = 5

    def countFloors(self):
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
        for floor in self.floors:
            count = sum(1 for dev in self.devices if self.extract_floor(dev['location']) == floor)
            self.n_dev_per_floor.append(count)
            print(f"number of parking per floor {floor}: {count}")

    def occDevPerFloorList(self):
        for floor in self.floors:
            count = sum(1 for dev in self.devices if self.extract_floor(dev['location']) == floor and dev['status'] in ("occupied", "reserved"))
            self.n_occ_dev_per_floor.append(count)
            print(f"number of occupied/booked parking for floor {floor}: {count}")

    @staticmethod
    def extract_floor(location):
        if location.startswith("P"):
            return location[1]
        return None

    def totalOccupied(self):
        self.tot_occupied = sum(1 for dev in self.devices if dev['status'] in ("occupied", "reserved"))
        print(f"total occupied parking slots: {self.tot_occupied}")

    def arrival_time(self):
        current_hour = datetime.datetime.now().hour
        if current_hour in range(0, 6) and self.tot_occupied < self.n_tot_dev:
            self.arrival_time = datetime.datetime.now() + datetime.timedelta(seconds=random.randint(0, self.t_hold_time))
            self.arrivals.append(self.arrival_time)
        elif current_hour in range(6, 24) and self.tot_occupied < self.n_tot_dev:
            self.arrival_time = datetime.datetime.now() + datetime.timedelta(seconds=random.randint(0, int(self.t_hold_time/2)))
            self.arrivals.append(self.arrival_time)
        self.arrivals.sort()

    def changeDevState(self, device, floor, time):
        if device['status'] == 'free' and self.extract_floor(device['location']) == floor:
            device['status'] = 'occupied'
            device['last_update'] = time.timestamp()
            device['booking_code'] = 'new_code'  # TODO: generate a unique code da levare
            #TODO: USE MQTT TO UPDATE 
            return True
        return False

    def get_free_device_on_floor(self, floor):
        for device in self.devices:
            if device['status'] == 'free' and self.extract_floor(device['location']) == floor:
                return device
        return None

    def routeArrivals(self):
        flag = 0
        time = datetime.datetime.now()
        if self.arrivals and time >= self.arrivals[0]:
            self.arrivals.pop(0)
            for floor in range(self.n_floors):
                if self.n_occ_dev_per_floor[floor] < int(0.8 * self.n_dev_per_floor[floor]):
                    device = self.get_free_device_on_floor(floor)
                    if device and self.changeDevState(device, floor, time):
                        print(f"Device {device['ID']} has changed state to {device['status']}")
                        print(f"device {device['ID']} has changed last update time to {device['last_update']}! \n")
                        print(f"device {device['ID']} has changed booking code to {device['booking_code']}! \n")
                        flag = 1
                        return device
                        #break


            if flag == 0:
                device = next((d for d in self.devices if d['status'] == 'free'), None)
                if device:
                    device['status'] = 'occupied'
                    device['last_update'] = time.timestamp()
                    device['booking_code'] = 'new_code'  # TODO: generate a unique code
                    #TODO: USE MQTT TO UPDATE
                    print(f"all floors have more than 80% of parkings occupied.\n")
                    print(f"Device {device['ID']} has changed state to {device['status']}")
                    print(f"device {device['ID']} has changed last update time to {device['last_update']}! \n")
                    print(f"device {device['ID']} has changed booking code to {device['booking_code']}! \n")
                    return device
                    
        #for booked
        

    def update_catalog(self, catalog_path):
        with open(catalog_path, 'w') as file:
            json.dump({"devices": self.devices}, file, indent=4)
            
    def handle_departures(self,catalog_path):
        departure_probability = 0.1  # 10% chance for any parked car to leave (JUST FOR SIMULATION, WE SHOULD HAVE 0.5)
        current_time = datetime.datetime.now()
        #POSSIBILITY TO DO A NEW BUCKET ON DB WHERE WE PUT DURATION, TIMESTAMP, FEE, FLOOR FOR CALCULATION OF STATISTICS FOR PROPETARY OF PARKING

        for device in self.devices:
            if device['status'] == 'occupied' and (device['booking_code']== "" or device['booking_code']== None):
                if random.random() < departure_probability:
                    device['status'] = 'free'
                    device['last_update'] = current_time.timestamp()
                    device['booking_code'] = "" # OR ""
                    #ADD FUNCTION TO CALCULATE FEE AND POST ON DB
                    print(f"Device {device['ID']} at {device['location']} is now free. Car has departed.")
                    #device oriented with topic to be received by adaptor who publishes on db
        self.update_catalog(catalog_path)
        
        
        
        


if __name__ == '__main__':


    catalog_path = "C:/Users/kevin/Documents/PoliTo/ProgrammingIOT/IoT_Project_/CATALOG/catalog.json"  
    if not os.path.exists(catalog_path):
        print("File not found:", catalog_path)
        exit(1)
    with open(catalog_path, 'r') as file:
        catalog = json.load(file)

    devices = catalog['devices']
    devices_by_floor = defaultdict(list)
    def extract_floor(location):
        if location.startswith("P"):
            return location[1]  # Extract the floor number (e.g., '0' for P0-1)
            return None
    for device in devices:
        floor = extract_floor(device['location'])
        if floor is not None:
            devices_by_floor[floor].append(device)
    devices_count_by_floor = {floor: len(devices) for floor, devices in devices_by_floor.items()}
    print("Devices by floor:")
    for floor, devices in devices_by_floor.items():
        print(f"Floor {floor}: {len(devices)} devices")
        for device in devices:
            print(f"  - Device {device['name']} at {device['location']} (Status: {device['status']})")

    print("\nTotal devices per floor:")
    print(devices_count_by_floor)


    # Loop for car arrivals and assignments, also handling departures
    try:
        while True:
            # Load the latest catalog (in case it was updated externally by departures)
            
            #TODO: DO IT WITH A GET TO ADAPTOR TO GET DEVICE LIST
            with open(catalog_path, 'r') as file:
                catalog = json.load(file)
            devices = catalog['devices']
            algorithm = Algorithm(devices)

            # Initialize the parking environment
            algorithm.countFloors()
            algorithm.countDev()
            algorithm.devPerFloorList()
            algorithm.occDevPerFloorList()
            algorithm.totalOccupied()
            # Recalculate the occupancy per floor based on the updated catalog
            algorithm.handle_departures(catalog_path)  
            algorithm.arrival_time()
            algorithm.routeArrivals()
            algorithm.update_catalog(catalog_path)
            time.sleep(5)
    except KeyboardInterrupt:
        False
        
        
#calcolo sordi
#booking code
#handling prenotati
#mettere db