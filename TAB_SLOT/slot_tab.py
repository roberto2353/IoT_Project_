import json
import time
import requests
from pathlib import Path
import paho.mqtt.client as PahoMQTT
from datetime import datetime
import sys

# Percorso assoluto alla cartella del progetto
#sys.path.append('/Users/alexbenedetti/Desktop/IoT_Project_')

#from DATA.event_logger import EventLogger

P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class SlotBoard:
    """Gestisce il tabellone per mostrare i posti liberi e occupati."""
    def __init__(self):
        self.free_slots = 0
        self.occupied_slots = 0
        self.total_slots = 0
        self.sensors_data = {}
        #self.event_logger = EventLogger()  # Istanza di EventLogger
        self.initialize_board()

    def initialize_board(self):
        """Inizializza il tabellone con il numero di posti totali, liberi e occupati."""
        try:
            with open(SETTINGS, "r") as fs:
                settings = json.loads(fs.read())
            url = settings["catalog_url"] + "/devices"
            response = requests.get(url)
            response.raise_for_status()
            slots = response.json().get('devices', [])
            self.total_slots = len(slots)
            print(f"Tabellone inizializzato: {self.total_slots} posti totali")

            # Inizializza il numero di posti liberi e occupati
            for slot in slots:
                slot_id = slot["ID"]
                status = slot.get("status", "unknown")
                self.sensors_data[slot_id] = status
                
                # Debug: Stampa lo stato di ogni slot per la verifica
                print(f"Inizializzazione slot {slot_id} con stato: {status}")
                
                if status == "free":
                    self.free_slots += 1
                elif status == "occupied":
                    self.occupied_slots += 1

            # Visualizza lo stato iniziale del tabellone
            self.display_board()

        except Exception as e:
            print(f"Errore nell'inizializzazione del tabellon: {e}")


    def update_slot(self, slot_id, status):
        """Aggiorna solo i conteggi dei posti liberi e occupati."""
        
        # Debug: stampa lo stato nuovo e il conteggio attuale
        print(f"Aggiornamento slot {slot_id}: Stato nuovo={status}")
        
        # Se lo slot diventa libero, decrementa i posti occupati e incrementa i posti liberi
        if status == "free":
            self.occupied_slots -= 1
            self.free_slots += 1

        # Se lo slot diventa occupato, decrementa i posti liberi e incrementa i posti occupati
        elif status == "occupied":
            self.free_slots -= 1
            self.occupied_slots += 1

        # Debug: stampa i nuovi conteggi
        print(f"Posti liberi aggiornati: {self.free_slots}, Posti occupati aggiornati: {self.occupied_slots}")
        self.display_board()



    def display_board(self):
        """Visualizza il tabellone con lo stato aggiornato."""
        print(f"Posti Liberi: {self.free_slots} | Posti Occupati: {self.occupied_slots} | Totale: {self.total_slots}")

class MySubscriber:
    def __init__(self, clientID, topic, message_callback):
        self.clientID = clientID
        self.topic = topic
        self.message_callback = message_callback
        self._paho_mqtt = PahoMQTT.Client(PahoMQTT.CallbackAPIVersion.VERSION2)
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

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

    def myOnConnect(self, client, userdata, flags, rc, properties=None):
        print(f"Connesso a {self.messageBroker} con codice di risultato: {rc}")
        if rc == 0:
            print("Sottoscrizione al topic...")
            self._paho_mqtt.subscribe(self.topic, self.qos)
            print(f"Sottoscritto al topic: {self.topic}")
        else:
            print("Errore nella connessione!")


    def myOnMessageReceived(self, client, userdata, msg):
        print(f"Messaggio ricevuto: Topic={msg.topic}, Payload={msg.payload.decode()}")
        self.message_callback(msg)

def main():
    slot_board = SlotBoard()

    def on_message_received(msg):
        """Callback per l'elaborazione dei messaggi MQTT ricevuti."""
        print(f"Messaggio ricevuto: Topic={msg.topic}, Payload={msg.payload.decode()}")

        try:
            data = json.loads(msg.payload.decode())
            print(f"Payload decodificato: {data}")
            event = data.get("e", [])[0]
            slot_status = event.get("v")
            slot_id = event.get("n").split("/")[0] 

            previous_status = slot_board.sensors_data.get(slot_id, "unknown")
            
            current_time = datetime.now()  
            last_change_time = slot_board.sensors_data.get(slot_id + "_time", current_time)
            duration = (current_time - last_change_time).total_seconds() if last_change_time else 0
            
            # Aggiorna lo stato del tabellone
            slot_board.update_slot(slot_id, slot_status)
            
            # Registra l'evento nel logger
            #slot_board.event_logger.log_event(slot_id, previous_status, slot_status, duration)
            
            # Aggiorna il tempo dell'ultimo cambiamento
            slot_board.sensors_data[slot_id + "_time"] = current_time
            
        except Exception as e:
            print(f"Errore nel processare il messaggio: {e}")

    # Inizializza il subscriber MQTT e inizia a ricevere aggiornamenti
    subscriber = MySubscriber("SlotTabSubscriber", "ParkingLot/+/status", on_message_received)
    subscriber.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        subscriber.stop()

if __name__ == '__main__':
    main()
