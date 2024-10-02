import paho.mqtt.client as PahoMQTT
import json

class MyPublisher:
    def __init__(self, clientID, topic, broker, port):
          self.clientID = clientID
          self.topic = topic
          self.messageBroker = broker
          self.port = port
          self._paho_mqtt = PahoMQTT.Client(PahoMQTT.CallbackAPIVersion.VERSION2) 
          self._paho_mqtt.clean_session = True  # Se necessario, imposta una clean session
          self._paho_mqtt.on_connect = self.myOnConnect

    def start(self):
        # Gestisce la connessione al broker MQTT utilizzando il port
        self._paho_mqtt.connect(self.messageBroker, self.port)
        self._paho_mqtt.loop_start()

    def stop(self):
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

    def myPublish(self, topic, message):
        print(f"Sto pubblicando su topic: {topic}")
        self._paho_mqtt.publish(topic, json.dumps(message), qos=2)


    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print("Connected to %s with result code: %d" % (self.messageBroker, rc))
