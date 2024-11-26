import json
import threading
import time
import cherrypy
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
    def __init__(self, settings):
        self.free_slots = 0
        self.occupied_slots = 0
        self.total_slots = 0
        self.sensors_data = {}
        self.catalogUrl = settings["catalog_url"]
        self.initialize_board()
        
    def initialize_board(self):
        """Inizializza il tabellone con il numero di posti totali, liberi e occupati."""
        try:
            #adaptor_url = 'http://127.0.0.1:8083/devices'  # Updated URL to match the CherryPy server
            parking_url = self.catalogUrl+"/parkings"
            response = requests.get(parking_url)
            response.raise_for_status()
            parkings = response.json().get("parkings", [])
            #parkings = response.json()
            #print(parkings)

            print("Parcheggi disponibili:")
            for idx, parking in enumerate(parkings):
                print(f"{idx + 1}. Nome: {parking['name']}, Indirizzo: {parking['url']}, Porta: {parking['port']}")

            # Chiedi all'utente di selezionare un parcheggio
            choice = int(input("Seleziona il numero del parcheggio da utilizzare: ")) - 1
            if choice < 0 or choice >= len(parkings):
                print("Selezione non valida. Riprova.")
                return

            # Ottieni i dettagli del parcheggio selezionato
            selected_parking = parkings[choice]
            devConnUrl = f"http://{selected_parking['url']}:{selected_parking['port']}/devices"
            print(f"Connettendosi al parcheggio: {selected_parking['name']}")

            # Ottieni i dispositivi del parcheggio selezionato
            response = requests.get(devConnUrl)
            response.raise_for_status()  # Verifica che la risposta sia corretta
            devices = response.json()
            print(f"Dispositivi nel parcheggio {selected_parking['name']}: {devices}")
            
            # Get the list of devices from the adaptor
            slots = response.json()
            if isinstance(slots, str): 
                final_data = json.loads(slots)
                print("Double-encoded JSON:", final_data)
            unique_ids = {device["deviceInfo"]["ID"] for device in final_data["devices"]}
            self.total_slots = len(unique_ids)
            print(f"Tabellone inizializzato: {self.total_slots} posti totali")

            # Inizializza il numero di posti liberi e occupati
            devices = final_data["devices"]
            for slot in devices:
                slot_id = slot["deviceInfo"]["ID"]
                status = slot["deviceInfo"]["status"]
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
            print(f"Errore nell'inizializzazione del tabellone: {e}")


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

    def __init__(self, clientID, settings, message_callback):

        self.clientID = clientID
        self.serviceInfo = settings["serviceInfo"]
        self.serviceID = self.serviceInfo["ID"]
        self.catalog_address = settings["catalog_url"]
        self.topic = settings["baseTopic"]+"/+/status"
        self.publish_topic = f"ParkingLotFabio/alive/{self.serviceID}"
        self.register_service()
        self.update_interval = settings["updateInterval"]  # Interval for periodic updates
        self.message_callback = message_callback
        self._paho_mqtt = PahoMQTT.Client(client_id=self.clientID)
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived
        self.messageBroker = settings["messageBroker"]
        self.port = settings["brokerPort"]
        self.qos = settings["qos"]

    def start(self):
        """Start the subscriber and publisher."""
        self._paho_mqtt.connect(self.messageBroker, self.port)
        self._paho_mqtt.loop_start()
        self._paho_mqtt.subscribe(self.topic, self.qos)
        print(f"Subscribed to topic: {self.topic}")

        self.start_periodic_updates()  

    def stop(self):
        """Stop the subscriber and publisher."""
        self._paho_mqtt.unsubscribe(self.topic)
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

    def myOnConnect(self, client, userdata, flags, rc, properties=None):
        print(f"Connected to {self.messageBroker} with result code: {rc}")
        if rc == 0:
            print("Subscribing to topic...")
            self._paho_mqtt.subscribe(self.topic, self.qos)
        else:
            print("Connection failed!")

    def myOnMessageReceived(self, client, userdata, msg):
        print(f"Message received: Topic={msg.topic}, Payload={msg.payload.decode()}")
        self.message_callback(msg)

    def publish_message(self, message):
        """Publish a message to the MQTT broker on the specified topic."""
        try:
            self._paho_mqtt.publish(self.publish_topic, json.dumps(message))
            print(f"Published message to {self.publish_topic}: {message}")
        except Exception as e:
            print(f"Error publishing message: {e}")

    def register_service(self):
        """Registers the service in the catalog using POST the first time."""
        #Next times, updated with MQTT
        
        # Initial POST request to register the service
        url = f"{self.catalog_address}/services"
        response = requests.post(url, json=self.serviceInfo)
        if response.status_code == 200:
            self.is_registered = True
            print(f"Service {self.serviceID} registered successfully.")
        else:
            print(f"Failed to register service: {response.status_code} - {response.text}")

    def start_periodic_updates(self):
        """Starts a background thread for periodic updates."""
        def periodic_update():
            time.sleep(10)
            while True:
                try:
                    message = {
                        "bn": "updateCatalogService",  
                        "e": [
                            {
                                "n": self.serviceID,  
                                "u": "IP",
                                "t": str(time.time()), 
                                "v": ""
                            }
                        ]
                    }
                    self.publish_message(message)
                    time.sleep(self.update_interval)
                except Exception as e:
                    print(f"Error during periodic update: {e}")

        # Start periodic updates in a background thread
        update_thread = threading.Thread(target=periodic_update, daemon=True)
        update_thread.start()
 

def main():
    settings = json.load(open(SETTINGS))
    slot_board = SlotBoard(settings)

    def recursive_json_decode(data):
        # Prova a decodificare fino a ottenere un dizionario o una lista
        while isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                break
        return data

    def on_message_received(msg):
        """Callback per l'elaborazione dei messaggi MQTT ricevuti."""
        print(f"Messaggio ricevuto: Topic={msg.topic}, Payload={msg.payload.decode()}")

        try:
            decoded_message = msg.payload.decode()
            print(f"Decoded message (first decode): {decoded_message}")

            # Decodifica ricorsiva fino a ottenere un dizionario o una lista
            data = recursive_json_decode(decoded_message)
            print(f"Final decoded message: {data}")
            print(f"Data type after final decode: {type(data)}")
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
    subscriber = MySubscriber("SlotTabSubscriber", settings, on_message_received)
    subscriber.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        subscriber.stop()

if __name__ == '__main__':
    main()