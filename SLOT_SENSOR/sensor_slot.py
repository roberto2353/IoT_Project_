from pathlib import Path
import time
import json
import random
from datetime import datetime
import requests
import threading
# Import MyPublisher and MyMQTT (assuming MyMQTT is a class that handles MQTT client management)
from simplePublisher import MyPublisher
from MyMQTT import MyMQTT

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class SlotSensor(MyPublisher):
    """Parking slot sensor simulator that listens to occupancy status."""

    def __init__(self, sensorID, baseTopic, slotCode, bookCode, broker, port):
        clientID = str(sensorID) + "Pub"
        if len(clientID) > 23:
            clientID = clientID[:23]  # Truncate if necessary

        super().__init__(clientID, baseTopic + "/status", broker, port)
        self.sensorID = sensorID
        self.slotCode = slotCode
        self.bookCode = bookCode
        self.isOccupied = False  # True if occupied, False if free
        self.last_state = False
        self.last_change_time = datetime.now()
        self.active = True
        self.pubTopic = f"{baseTopic}/status"
        self.aliveTopic = f"ParkingLot/alive/{self.slotCode}"
        self.simulate_occupancy = True

        self.client = MyMQTT(self.sensorID, broker, port, None)


    def updateState(self):
        while self.active:
            if self.bookCode == "":
                new_state = random.choice([True, False])  # True if occupied, False if free
                new_state_str = "occupied" if new_state else "free"
                last_state_str = "occupied" if self.last_state else "free"

                if new_state != self.isOccupied:
                    current_time = datetime.now()
                    duration = (current_time - self.last_change_time).total_seconds()
                    self.last_change_time = current_time
                    self.last_state = new_state
                    self.isOccupied = new_state
                    print(f"Slot {self.slotCode} status changed from: {last_state_str} to {new_state_str}")

                    event = {
                        "n": f"{self.slotCode}/status", "u": "boolean", "t": str(time.time()), "v": new_state_str
                    }
                    message = {"bn": self.pubTopic, "e": [event]}
                    self.client.myPublish(self.pubTopic, json.dumps(message))

                    self.update_catalog_state(new_state_str, self.sensorID)
            time.sleep(10)  # Check for state change every 10 seconds

    def update_catalog_state(self, new_state, sensorId):
        """Update sensor state in the catalog."""
        try:
            with open(SETTINGS, "r") as fs:
                settings = json.loads(fs.read())

            catalog_url = f"{settings['catalog_url']}/devices"
            response = requests.get(catalog_url)
            response.raise_for_status()
            devices = response.json().get('devices', [])

            for device in devices:
                if device.get("ID") == sensorId:
                    device["status"] = new_state
                    device["last_update"] = time.time()
                    break

            response = requests.put(catalog_url, json=device)
            response.raise_for_status()
            print(f"Sensor {self.slotCode} status updated in catalog to: {new_state}")
        
        except Exception as e:
            print(f"Error updating catalog for sensor {self.slotCode}: {e}")

    def start(self):
        self.client.start()
        self.active = True
        threading.Thread(target=self.sendDataAlive, daemon=True).start()
        threading.Thread(target=self.updateState, daemon=True).start()

    def stop(self):
        self.client.stop()
        self.active = False
    
    def sleepyTime(self,hour):
        #1h ->3600s
        if hour in range(0,6):
            time.sleep(3600*3)
        else :
            time.sleep(1800) #half an hour
            
    def powerNap(self,hour):
        
        if hour in range(0,6):
            time.sleep(3)
        else :
            time.sleep(1) #half an hour
        


# Main function to initialize and run SlotSensors
if __name__ == '__main__':
    current_hour = datetime.now().hour
    conf = json.load(open(SETTINGS))
    owner = input("Enter your name: ")
    baseTopic = conf["baseTopic"]
    broker = conf["messageBroker"]
    port = conf["brokerPort"]
    catalog_url = conf["catalog_url"]

    sensors = []
    sensorID = 0

    response = requests.get(catalog_url + "/devices")
    response.raise_for_status()
    devices = response.json().get('devices', [])

    for device in devices:
        sensorID = device.get("ID")
        slotCode = device.get("location")
        bookCode = device.get("booking_code", "") # empty  "" or bookcode
        sensor = SlotSensor(sensorID, baseTopic, slotCode, bookCode, broker, port)
        sensors.append(sensor)

    for sensor in sensors:
        sensor.start()

    try:
        while True:
            #sensor.sleepyTime(current_hour)
            #time.sleep(1)
            sensor.powerNap(current_hour)

    except KeyboardInterrupt:
        for sensor in sensors:
            sensor.stop()
