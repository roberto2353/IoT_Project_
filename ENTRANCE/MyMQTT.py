import json
import paho.mqtt.client as PahoMQTT

class MyMQTT:
    def __init__(self, clientID, broker, port, notifier):
        self.broker = broker
        self.port = port
        self.notifier = notifier
        self.clientID = str(clientID)
        self._topic = ""
        self._isSubscriber = False
        self._paho_mqtt = PahoMQTT.Client(PahoMQTT.CallbackAPIVersion.VERSION2) 
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

    def myOnConnect(self, client, userdata, flags, rc, properties=None):
        print(f"Connected to  {self.broker} with result code: {str(rc)}")

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        if self.notifier is not None:
            self.notifier.notify(msg.topic, msg.payload)

    def myPublish(self, topic, msg):
        self._paho_mqtt.publish(topic, json.dumps(msg), qos=2)
        print(f"Message published on topic {topic}: {json.dumps(msg)}")

    def start(self):
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def stop(self):
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
