import paho.mqtt.client as mqtt
import json
import time

# Callback che viene chiamato quando il client si connette al broker
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connesso con successo al broker!")
        # Prova a pubblicare un messaggio di test
        message = {"test": "message"}
        client.publish("ParkingLot/test/status", json.dumps(message), qos=1)
        print("Messaggio di test pubblicato")
    else:
        print(f"Errore di connessione. Codice di errore: {rc}")

# Callback che viene chiamato quando il messaggio viene pubblicato
def on_publish(client, userdata, mid):
    print("Messaggio pubblicato correttamente!")

# Callback che viene chiamato quando si verifica un errore
def on_log(client, userdata, level, buf):
    print(f"Log: {buf}")

# Configura il client MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

client.on_connect = on_connect
client.on_publish = on_publish
client.on_log = on_log  # Aggiungiamo anche un log per avere informazioni su eventuali errori

# Connessione al broker
client.connect("mqtt.eclipseprojects.io", 1883, 60)

# Avvia il loop in background
client.loop_start()

# Aggiungiamo una pausa per dare il tempo alla pubblicazione
time.sleep(5)

# Ferma il loop e disconnetti
client.loop_stop()
client.disconnect()
