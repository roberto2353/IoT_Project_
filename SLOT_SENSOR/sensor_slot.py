from pathlib import Path
import paho.mqtt.client as PahoMQTT
import time
from queue import Queue
import json
import requests
import random
import sys
from datetime import datetime

# Percorso assoluto alla cartella del progetto
sys.path.append('"C:/Users/kevin/Documents/PoliTo/ProgrammingIOT/IoT_Project_"')

from DATA.event_logger import EventLogger

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class SlotSensor:
    """Parking slot sensor simulator that listens to occupancy status."""
    def __init__(self, sensorId, baseTopic, slotCode):
        self.sensorId = sensorId
        self.isOccupied = False  # True if occupied, False if free
        self.last_state = False
        self.last_change_time = datetime.now()
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
        new_state = random.choice([True, False])  # True if occupied, False if free

        new_state_str = "occupied" if new_state else "free"
        last_state_str = "occupied" if self.last_state else "free"

        if new_state != self.isOccupied:
            current_time = datetime.now()
            duration = (current_time - self.last_change_time).total_seconds()  # Duration in seconds
            self.event_logger.log_event(self.slotCode, last_state_str, new_state_str, duration)
            self.last_change_time = current_time
            self.last_state = new_state
            self.isOccupied = new_state
            print(f"Slot {self.slotCode} stato aggiornato da: {last_state_str} a {new_state_str}")

            # Pubblica lo stato corrente
            event = {"n": self.slotCode + "/status", "u": "boolean", "t": str(time.time()), "v": new_state_str}
            out = {"bn": self.pubTopic, "e": [event]}
            self.myPub.myPublish(json.dumps(out), self.pubTopic)

            # Aggiorna lo stato del sensore nel catalogo
            self.update_catalog_state(new_state_str)

            # Pubblica il messaggio di vitalità
            eventAlive = {"n": self.slotCode + "/status", "u": "IP", "t": str(time.time()), "v": ""}
            outAlive = {"bn": self.aliveBn, "e": [eventAlive]}
            self.myPub.myPublish(json.dumps(outAlive), self.aliveTopic)

    def update_catalog_state(self, new_state):
        """Invia una richiesta PUT per aggiornare lo stato del sensore nel catalogo."""
        try:
            with open(SETTINGS, "r") as fs:
                settings = json.loads(fs.read())
            
            catalog_url = settings["catalog_url"]
            url = f"{catalog_url}/devices"

            # Ottieni i dati attuali dal catalogo
            response = requests.get(url)
            response.raise_for_status()
            devices = response.json().get('devices', [])
            
            # Trova il dispositivo nel catalogo e aggiorna il suo stato
            for device in devices:
                if device["location"] == self.slotCode:
                    device["status"] = new_state
                    device["last_update"] = time.time()
                    break

            # Invia la richiesta PUT per aggiornare lo stato nel catalogo
            response = requests.put(url, json=device)
            response.raise_for_status()
            print(f"Stato del sensore {self.slotCode} aggiornato nel catalogo a: {new_state}")
        
        except Exception as e:
            print(f"Errore durante l'aggiornamento del catalogo per il sensore {self.slotCode}: {e}")

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
            
        time.sleep(35) 


if __name__ == '__main__':
    main()
