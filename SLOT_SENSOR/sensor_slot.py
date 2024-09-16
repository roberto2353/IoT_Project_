from pathlib import Path
import time
import json
import random
from datetime import datetime
import requests

# Import MyPublisher and MyMQTT (assuming MyMQTT is a class that handles MQTT client management)
from simplePublisher import MyPublisher
from MyMQTT import MyMQTT

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class SlotSensor(MyPublisher):
    """Parking slot sensor simulator that listens to occupancy status."""

    def __init__(self, sensorID, baseTopic, slotCode, broker, port):
        clientID = str(sensorID) + "Pub"
        if len(clientID) > 23:
            clientID = clientID[:23]  # Troncamento se necessario

        # Passaggio dell'ID corretto al costruttore del parent
        super().__init__(clientID, baseTopic + "/status", broker, port)
        self.sensorID = sensorID
        self.sensorID = sensorID
        self.slotCode = slotCode
        self.isOccupied = False  # True if occupied, False if free
        self.last_state = False
        self.last_change_time = datetime.now()
        self.active = True
        self.pubTopic = f"{baseTopic}/status"
        self.aliveTopic = f"ParkingLot/alive/{self.slotCode}"
        self.simulate_occupancy = True

        # Initialize the MyMQTT client for managing MQTT connections
        self.client = MyMQTT(self.sensorID, broker, port, None)

        # Event logger to track state changes
        #self.event_logger = EventLogger()

    def sendDataAlive(self):
            # Send alive message to indicate the sensor is still active
            eventAlive = {"n": f"{self.slotCode}/status", "u": "IP", "t": str(time.time()), "v": ""}
            aliveMessage = {"bn": "updateCatalogSlot", "e": [eventAlive]}
            self.client.myPublish(self.aliveTopic, json.dumps(aliveMessage))  # Publish alive message
    
    def updateState(self):
        """Simulates state change and sends the data via MQTT."""
        new_state = random.choice([True, False])  # True if occupied, False if free
        new_state_str = "occupied" if new_state else "free"
        last_state_str = "occupied" if self.last_state else "free"

        # Check if there's a state change
        if new_state != self.isOccupied:
            current_time = datetime.now()
            duration = (current_time - self.last_change_time).total_seconds()
            #self.event_logger.log_event(self.slotCode, last_state_str, new_state_str, duration)
            self.last_change_time = current_time
            self.last_state = new_state
            self.isOccupied = new_state
            print(f"Slot {self.slotCode} stato aggiornato da: {last_state_str} a {new_state_str}")

            # Create and publish MQTT message
            event = {
                "n": f"{self.slotCode}/status", "u": "boolean", "t": str(time.time()), "v": new_state_str
            }
            message = {"bn": self.pubTopic, "e": [event]}
            self.client.myPublish(self.pubTopic, json.dumps(message))  # Using self.client to publish message

            # Update sensor state in the catalog
            self.update_catalog_state(new_state_str,self.sensorID)

    

    def update_catalog_state(self, new_state, sensorId):
        """Update sensor state in the catalog."""
        try:
            with open(SETTINGS, "r") as fs:
                settings = json.loads(fs.read())

            catalog_url = f"{settings['catalog_url']}/devices"

            # Get current devices from the catalog
            response = requests.get(catalog_url)
            response.raise_for_status()
            devices = response.json().get('devices', [])

            # Find and update the device in the catalog
            for device in devices:
                if(device.get("ID") == sensorId):
                    device["status"] = new_state
                    device["last_update"] = time.time()
                    break

            # Send PUT request to update the catalog
            response = requests.put(catalog_url, json=device)
            response.raise_for_status()
            print(f"Stato del sensore {self.slotCode} aggiornato nel catalogo a: {new_state}")
        
        except Exception as e:
            print(f"Errore durante l'aggiornamento del catalogo per il sensore {self.slotCode}: {e}")

    def start(self):
        """Start the MQTT client."""
        self.client.start()  # Start MQTT client connection

    def stop(self):
        """Stop the MQTT client."""
        self.client.stop()  # Stop MQTT client connection


# Main function to initialize and run SlotSensors
if __name__ == '__main__':
    conf = json.load(open(SETTINGS))
    owner = input("Enter your name ")
    baseTopic = conf["baseTopic"]
    broker = conf["messageBroker"]
    port = conf["brokerPort"]
    catalog_url = conf["catalog_url"]

    sensors = []
    sensorID = 0

    response = requests.get(catalog_url+"/devices")
    response.raise_for_status()
    devices = response.json().get('devices', [])

    for device in devices: 
        sensorID = device.get("ID") 
        slotCode = device.get("location")
        sensor = SlotSensor(sensorID, baseTopic, slotCode, broker, port)
        sensors.append(sensor)

    for sensor in sensors:
        sensor.start()

    try:
        while True:
            for sensor in sensors:
                sensor.sendDataAlive()
                time.sleep(1)

    except KeyboardInterrupt:
        for sensor in sensors:
            sensor.stop()
