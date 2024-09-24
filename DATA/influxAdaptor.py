import paho.mqtt.client as PahoMQTT
import time
import json
from influxdb import InfluxDBClient
import sys
import cherrypy
import requests  # Assicurati di avere importato requests

class dbAdaptor:
    exposed = True  # Esponi la classe per CherryPy

    def __init__(self, clientID, topic=None, influx_host='localhost', influx_port=8086, influx_user='root', influx_password='root', influx_db='IoT_Smart_Parking'):
        self.clientID = clientID
        # Crea un'istanza di paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client(clientID, True)

        # Registra i callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

        if topic is None:
            self.topic = 'ParkingLot/+/status'
        else:
            self.topic = topic

        self.messageBroker = 'mqtt.eclipseprojects.io'

        # Configurazione del client InfluxDB
        self.client = InfluxDBClient(host=influx_host, port=influx_port, username=influx_user, password=influx_password, database=influx_db)
        if {'name': influx_db} not in self.client.get_list_database():
            self.client.create_database(influx_db)

    def start(self):
        # Gestisci la connessione al broker
        self._paho_mqtt.connect(self.messageBroker, 1883)
        self._paho_mqtt.loop_start()
        # Iscrivi al topic
        self._paho_mqtt.subscribe(self.topic, 2)

    def stop(self):
        self._paho_mqtt.unsubscribe(self.topic)
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print(f"Connected to {self.messageBroker} with result code: {rc}")

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        # Un nuovo messaggio viene ricevuto
        print(f"Topic:'{msg.topic}', QoS: '{msg.qos}' Message: '{msg.payload.decode()}'")
        try:
            data = json.loads(msg.payload.decode())
            json_body = [
                {
                    "measurement": 'status',
                    "tags": {
                        "slotID": data['id'],
                        "type": data['type'],
                        "location": data['location']
                    },
                    "time": int(time.time()),
                    "fields": {
                        "name": data['name'],
                        "status": data.get('status', 'unknown'),
                        "booking_code": data.get('booking_code', '')
                    }
                }
            ]
            self.client.write_points(json_body, time_precision='s')
        except Exception as e:
            print(e)

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, *uri, **params):
        if len(uri) == 0:
            raise cherrypy.HTTPError(400, "Endpoint not specified")
        
        if uri[0] == 'register_device':
            try:
                device_info = cherrypy.request.json
                required_fields = ['ID', 'name', 'type', 'location']
                for field in required_fields:
                    if field not in device_info:
                        return {"error": f"Missing field: {field}"}, 400
                
                json_body = [
                    {
                        "measurement": 'status',
                        "tags": {
                            "ID": str(device_info['ID']),
                            "type": device_info['type'],
                            "location": device_info['location']
                        },
                        "time": int(time.time()),  # Timestamp corrente
                        "fields": {
                            "name": device_info['name'],
                            "status": device_info.get('status', 'unknown'),
                            "booking_code": device_info.get('booking_code', '')
                        }
                    }
                ]
                self.client.write_points(json_body)  # Correggi l'attributo
                print(f"Registered device with ID {device_info['ID']} on InfluxDB.")
                return {"message": f"Device with ID {device_info['ID']} registered successfully."}, 201
            
            except Exception as e:
                print(f"Error registering device: {e}")
                return {"error": str(e)}, 500
        else:
            raise cherrypy.HTTPError(404, "Endpoint not found")

    def GET(self, *uri, **params):
        # Implementa eventualmente un metodo GET per verificare lo stato
        raise cherrypy.HTTPError(405, "Method not allowed")

if __name__ == "__main__":
    test = dbAdaptor('IoT_Smart_Parking')
    test.start()
    
    # Configurazione di CherryPy con MethodDispatcher
    config = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        }
    }

    cherrypy.config.update({
        'server.socket_host': '127.0.0.1',
        'server.socket_port': 5000,
        'engine.autoreload.on': False
    })

    # Monta il servizio su /
    cherrypy.tree.mount(test, '/', config)
    
    try:
        cherrypy.engine.start()
        print("dbAdaptor service started on port 5000.")
        cherrypy.engine.block()
    except KeyboardInterrupt:
        print("Shutting down dbAdaptor service...")
    finally:
        test.stop()
        cherrypy.engine.exit()
