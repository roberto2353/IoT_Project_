from pathlib import Path
import paho.mqtt.client as PahoMQTT
import json
import time
import requests
from paho.mqtt.client import CallbackAPIVersion
import sys

# Percorso assoluto alla cartella del progetto
sys.path.append('/Users/alexbenedetti/Desktop/IoT_Project_')

from DATA.event_logger import EventLogger


P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class SlotBoard:
    """Gestisce il tabellone per mostrare i posti liberi e occupati."""
    def __init__(self):
        self.free_slots = 0
        self.occupied_slots = 0
        self.total_slots = 0
        self.sensors_data = {}
        self.event_logger = EventLogger()  # Istanza di EventLogger
        self.initialize_board()

    def initialize_board(self):
        try:
            with open(SETTINGS, "r") as fs:
                settings = json.loads(fs.read())
            url = settings["catalog_url"] + "/devices"
            response = requests.get(url)
            response.raise_for_status()
            slots = response.json().get('devices', [])
            self.total_slots = len(slots)
            print(f"Tabellone inizializzato: {self.total_slots} posti totali")
        except Exception as e:
            print(f"Errore nell'inizializzazione del tabellone: {e}")

    def update_slot(self, slot_id, status):
        previous_status = self.sensors_data.get(slot_id, "unknown")  # Default a 'unknown' se non presente
        if previous_status == status:
            return  # Non fare nulla se lo stato non cambia

        self.sensors_data[slot_id] = status
        if status == "free":
            if previous_status == "occupied":
                self.occupied_slots -= 1
            self.free_slots += 1
        elif status == "occupied":
            if previous_status == "free":
                self.free_slots -= 1
            self.occupied_slots += 1

        # Registra l'evento nel database
        self.event_logger.log_event(slot_id, previous_status, status)

        print(f"Slot aggiornato: {slot_id} - Stato: {status}")
        print(f"Posti liberi: {self.free_slots}, Posti occupati: {self.occupied_slots}")
        self.display_board()

    def display_board(self):
        print(f"Posti Liberi: {self.free_slots} | Posti Occupati: {self.occupied_slots} | Totale: {self.total_slots}")

class MySubscriber:
    def __init__(self, clientID, topic, message_callback):
        self.clientID = clientID
        self.topic = topic
        self.message_callback = message_callback
        self._paho_mqtt = PahoMQTT.Client(
            client_id=self.clientID,
            clean_session=False,
            
        )

        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

        # Configura il broker MQTT
        try:
            with open(SETTINGS, "r") as fs:
                self.settings = json.loads(fs.read())
        except Exception:
            print("Problema nel caricamento delle impostazioni")
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

    def myOnConnect(self, client, userdata, flags, rc):
        print(f"Connesso a {self.messageBroker} con codice di risultato: {rc}")
        if rc == 0:
            print("Sottoscrizione al topic...")
            self._paho_mqtt.subscribe(self.topic, self.qos)
        else:
            print("Errore nella connessione!")

    def myOnMessageReceived(self, client, userdata, msg):
        print(f"Messaggio ricevuto: Topic={msg.topic}, Payload={msg.payload.decode()}") 
        self.message_callback(msg)



def main():
    slot_board = SlotBoard()

    def on_message_received(msg):
        try:
            data = json.loads(msg.payload.decode())  # Aggiunta .decode() per leggere il payload come stringa
            print(f"Payload decodificato: {data}")  # Debugging
            event = data.get("e", [])[0]
            slot_status = event.get("v")
            slot_id = event.get("n").split("/")[0]  # Assumendo che "n" contenga l'ID del posto
            slot_board.update_slot(slot_id, slot_status)
        except Exception as e:
            print(f"Errore nel processare il messaggio: {e}")

    subscriber = MySubscriber("SlotTabSubscriber", "ParkingLot/+/+/status", on_message_received)
    subscriber.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        subscriber.stop()

if __name__ == '__main__':
    main()
