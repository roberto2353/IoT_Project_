from pathlib import Path
import paho.mqtt.client as PahoMQTT
import time
from queue import Queue
import json
import requests
import random
import sys

# Percorso assoluto alla cartella del progetto
sys.path.append('/Users/alexbenedetti/Desktop/IoT_Project_')

from DATA.event_logger import EventLogger

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class SlotSensor:
    """Parking slot sensor simulator that listens to occupancy status."""
    def __init__(self, sensorId, baseTopic, slotCode):
        self.sensorId = sensorId
        self.isOccupied = False  # True if occupied, False if free
        self.active = True
        self.pubTopic = baseTopic + "/status"
        self.subTopic = baseTopic + "/+"  # Subscribe to all messages under baseTopic
        self.aliveBn = "updateCatalogSlot"
        self.slotCode = slotCode
        self.aliveTopic = "ParkingLot/alive/" + self.slotCode  # Definizione di aliveTopic
        self.simulate_occupancy = True  
        self.myPub = MyPublisher(self.sensorId + "Pub", self.pubTopic)
        self.mySub = MySubscriber(self.sensorId + "Sub1", self.subTopic)
        self.myPub.start()
        self.mySub.start()
        self.event_logger = EventLogger()
        

    def update_state(self):
    # Stato precedente per il logging
        previous_state = "occupied" if self.isOccupied else "free"
        
        # Simula cambiamenti di stato
        if self.simulate_occupancy:
            self.isOccupied = random.choice([True, False])
        
        # Nuovo stato
        new_state = "occupied" if self.isOccupied else "free"

        # Controllo se lo stato è cambiato
        if new_state != previous_state:
            print(f"Slot {self.slotCode} stato aggiornato da: {previous_state} a {new_state}")

            # Pubblica lo stato corrente
            event = {"n": self.slotCode + "/status", "u": "boolean", "t": str(time.time()), "v": new_state}
            out = {"bn": self.pubTopic, "e": [event]}
            self.myPub.myPublish(json.dumps(out), self.pubTopic)

            # Registra l'evento nel database InfluxDB
            self.event_logger.log_event(self.slotCode, previous_state, new_state)

            # Pubblica il messaggio di vitalità
            eventAlive = {"n": self.slotCode + "/status", "u": "IP", "t": str(time.time()), "v": ""}
            outAlive = {"bn": self.aliveBn, "e": [eventAlive]}
            self.myPub.myPublish(json.dumps(outAlive), self.aliveTopic)


    def toggle_simulation(self):
        # Attiva o disattiva la simulazione
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
        data = response.json()  # Parse JSON response

        # Now access the 'devices' key in the JSON object
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

    def start(self):
        self._paho_mqtt.connect(self.messageBroker, self.port)
        self._paho_mqtt.loop_start()

    def stop(self):
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

    def myPublish(self, message, topic):
        print(f"Pubblicazione messaggio su topic {topic}: {message}")  # Debugging
        self._paho_mqtt.publish(topic, message, self.qos)

    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print(f"Connected to {self.messageBroker} with result code: {rc}")


class MySubscriber:
    def __init__(self, clientID, topic):
        self.clientID = clientID + "slotsub"
        self.q = Queue()
        self._paho_mqtt = PahoMQTT.Client(client_id=self.clientID, clean_session=False, userdata=None, protocol=PahoMQTT.MQTTv311, transport="tcp")
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived
        self.topic = topic

        try:
            with open(SETTINGS, "r") as fs:                
                self.settings = json.loads(fs.read())            
        except Exception:
            print("Problem in loading settings")
            return
        self.messageBroker = self.settings["messageBroker"]
        self.port = self.settings["brokerPort"]
        self.qos = self.settings["qos"]

    def start(self):
        self._paho_mqtt.connect(self.messageBroker, self.port)
        self._paho_mqtt.loop_start()
        self._paho_mqtt.subscribe(self.topic, self.qos)

    def stop(self):
        self._paho_mqtt.unsubscribe(self.topic)
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print(f"Connected to {self.messageBroker} with result code: {rc}")

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        if msg.topic.split("/")[3] in ["occupancy"]:
            self.q.put(msg)
            print(f"Topic: '{msg.topic}', QoS:'{msg.qos}' Message: '{msg.payload}'")


def main():
    """Funzione principale che esegue continuamente il processamento dei dati dei sensori di parcheggio."""
    sensors = []

    
    for sens in sensors:
        sens.toggle_simulation()  

    while True:
        update_sensors(sensors)  
        for sens in sensors:
            sens.update_state()  
            
        time.sleep(10) 


if __name__ == '__main__':
    main()
