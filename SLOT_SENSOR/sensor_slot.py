from pathlib import Path
import time
import json
import random
from datetime import datetime
import requests

<<<<<<< HEAD
# Percorso assoluto 
sys.path.append('/Users/robertobratu/Desktop/IoT_Project_')

from DATA.event_logger import EventLogger
=======
# Import MyPublisher and MyMQTT (assuming MyMQTT is a class that handles MQTT client management)
from simplePublisher import MyPublisher
from MyMQTT import MyMQTT
>>>>>>> 9f245e5cf528035f86a09f89934ea97dad5d3709

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
        self.slotCode = slotCode
        self.isOccupied = False  # True if occupied, False if free
        self.last_state = False
        self.last_change_time = datetime.now()
        self.active = True
<<<<<<< HEAD
        self.pubTopic = baseTopic + "/status"
        self.subTopic = baseTopic + "/+"  # Subscribe to all messages under baseTopic
        self.aliveBn = "updateCatalogSlot"
        self.slotCode = slotCode
        self.aliveTopic = "ParkingLot/alive/" + self.slotCode  
        self.simulate_occupancy = True  
        self.myPub = MyPublisher(self.sensorId + "Pub", self.pubTopic)
        self.mySub = MySubscriber(self.sensorId + "Sub1", self.subTopic)
        self.myPub.start()
        self.mySub.start()
        self.event_logger = EventLogger()

    def update_state(self):
        new_state = random.choice([True, False])  # True if occupied, False if free
=======
        self.pubTopic = f"{baseTopic}/{self.slotCode}/status"
        self.aliveTopic = f"ParkingLot/alive/{self.slotCode}"
        self.simulate_occupancy = True

        # Initialize the MyMQTT client for managing MQTT connections
        self.client = MyMQTT(self.sensorID, broker, port, None)
>>>>>>> 9f245e5cf528035f86a09f89934ea97dad5d3709

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

<<<<<<< HEAD
            # Pubblica il nuovo stato del sensore
            event = {"n": self.slotCode + "/status", "u": "boolean", "t": str(time.time()), "v": new_state_str}
            out = {"bn": self.pubTopic, "e": [event]}
            self.myPub.myPublish(json.dumps(out), self.pubTopic)
=======
            # Create and publish MQTT message
            event = {
                "n": f"{self.slotCode}/status", "u": "boolean", "t": str(time.time()), "v": new_state_str
            }
            message = {"bn": self.pubTopic, "e": [event]}
            self.client.myPublish(self.pubTopic, json.dumps(message))  # Using self.client to publish message
>>>>>>> 9f245e5cf528035f86a09f89934ea97dad5d3709

            # Update sensor state in the catalog
            self.update_catalog_state(new_state_str,self.sensorID)

<<<<<<< HEAD
            # Pubblica un messaggio di "alive" per notificare che il sensore è attivo
            eventAlive = {"n": self.slotCode + "/status", "u": "IP", "t": str(time.time()), "v": ""}
            outAlive = {"bn": self.aliveBn, "e": [eventAlive]}
            self.myPub.myPublish(json.dumps(outAlive), self.aliveTopic)
=======
    
>>>>>>> 9f245e5cf528035f86a09f89934ea97dad5d3709

    def update_catalog_state(self, new_state, sensorId):
        """Update sensor state in the catalog."""
        try:
            with open(SETTINGS, "r") as fs:
                settings = json.loads(fs.read())

<<<<<<< HEAD
            # Ottieni la lista dei dispositivi dal catalogo
            response = requests.get(url)
            response.raise_for_status()
            devices = response.json().get('devices', [])
            
            
=======
            catalog_url = f"{settings['catalog_url']}/devices"

            # Get current devices from the catalog
            response = requests.get(catalog_url)
            response.raise_for_status()
            devices = response.json().get('devices', [])

            # Find and update the device in the catalog
>>>>>>> 9f245e5cf528035f86a09f89934ea97dad5d3709
            for device in devices:
                if(device.get("ID") == sensorId):
                    device["status"] = new_state
                    device["last_update"] = time.time()
                    break

<<<<<<< HEAD
            # Invia una richiesta PUT per aggiornare il catalogo
            response = requests.put(url, json=device)
=======
            # Send PUT request to update the catalog
            response = requests.put(catalog_url, json=device)
>>>>>>> 9f245e5cf528035f86a09f89934ea97dad5d3709
            response.raise_for_status()
            print(f"Stato del sensore {self.slotCode} aggiornato nel catalogo a: {new_state}")
        
        except Exception as e:
            print(f"Errore durante l'aggiornamento del catalogo per il sensore {self.slotCode}: {e}")

<<<<<<< HEAD
    def toggle_simulation(self):
        self.simulate_occupancy = not self.simulate_occupancy
    
    def stop(self):
        self.mySub.stop()
        self.myPub.stop()
        
    def setActiveFalse(self):
        self.active = False
        
    def setActiveTrue(self):
        self.active = True


def update_sensors(sensors):
    """Updates list of sensors by checking any update in the catalog."""
    try:
        with open(SETTINGS, "r") as fs:
            settings = json.loads(fs.read())
    except Exception as e:
        print(f"Problem in loading settings: {e}")
        return

    url = settings["catalog_url"] + "/devices"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()  

       
        if 'devices' not in data:
            print(f"Unexpected response format: {data}")
            return

        slots = data['devices']  # Extract the list of devices
    except requests.exceptions.RequestException as e:
        print(f"HTTP request failed: {e}")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return

    # Check if any new sensors need to be added
    for slot in slots:
        sensId = slot["location"]  # Assuming 'location' is the unique identifier
        found = False
        for sens in sensors:
            if sens.sensorId == sensId:
                found = True
        if not found:
            baseTopic = "ParkingLot/" + slot["name"] + "/" + slot["location"]
            sens = SlotSensor(sensId, baseTopic, slot["location"])
            sensors.append(sens)

    # Remove sensors that are no longer in the catalog
    for sens in sensors[:]:
        found = False
        for slot in slots:
            sensId = slot["location"]
            if sens.sensorId == sensId:
                found = True
        if not found:
            sensors.remove(sens)


class MyPublisher:
    def __init__(self, clientID, topic):
        self.clientID = clientID + "status"
        self.topic = topic
        self._paho_mqtt = PahoMQTT.Client(client_id=self.clientID, clean_session=False, userdata=None, protocol=PahoMQTT.MQTTv311, transport="tcp")
        self._paho_mqtt.on_connect = self.myOnConnect

        try:
            with open(SETTINGS, "r") as fs:                
                self.settings = json.loads(fs.read())            
        except Exception:
            print("Problem in loading settings")
            return
        self.messageBroker = self.settings["messageBroker"]
        self.port = self.settings["brokerPort"]
        self.qos = self.settings["qos"]

=======
>>>>>>> 9f245e5cf528035f86a09f89934ea97dad5d3709
    def start(self):
        """Start the MQTT client."""
        self.client.start()  # Start MQTT client connection

    def stop(self):
<<<<<<< HEAD
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

    def myPublish(self, message, topic):
        print(f"Pubblicazione messaggio su topic {topic}: {message}")  # Debug
        self._paho_mqtt.publish(topic, message, self.qos)

    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print(f"Connected to {self.messageBroker} with result code: {rc}")
=======
        """Stop the MQTT client."""
        self.client.stop()  # Stop MQTT client connection
>>>>>>> 9f245e5cf528035f86a09f89934ea97dad5d3709


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
