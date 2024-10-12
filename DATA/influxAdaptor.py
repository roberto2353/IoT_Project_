import paho.mqtt.client as PahoMQTT
import time
import json
from datetime import datetime
from influxdb import InfluxDBClient
import sys
import cherrypy
import requests  

class dbAdaptor:
    exposed = True  # Esponi la classe per CherryPy

    def __init__(self, clientID, topic=None, influx_host='localhost', influx_port=8086, influx_user='root', influx_password='root', 
                 influx_db='IoT_Smart_Parking', influx_stats = 'IoT_SP_Stats'):
        self.clientID = clientID
        self.influx_stats = influx_stats
        self.influx_db = influx_db
        # Crea un'istanza di paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client("fabio", True)

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
        if {'name': influx_stats} not in self.client.get_list_database():
            self.client.create_database(influx_stats)

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

    def myOnConnect(self, paho_mqtt, userdata, flags, reasonCode, properties=None):
        print(f"Connected to {self.messageBroker} with result code: {reasonCode}")


    def recursive_json_decode(self, data):
        # Prova a decodificare fino a ottenere un dizionario o una lista
        while isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                break
        return data
    def update_stats_db(self,data):
        fee = data.get('fee', 'unknown')
        floor = data.get('floor')
        booking_code = data.get('booking_code', 'unknown')
        duration = data.get('duration')
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sensor_id = data.get('sensor_id')
        json_body = [
                        {
                            "measurement": 'status',
                            "tags": {
                                "ID": sensor_id,
                                "floor": floor
                            },
                            "time": str(current_time),  # Timestamp corrente
                            "fields": {
                                "booking_code": booking_code,  # Codice di prenotazione
                                "duration": duration,
                                "fee": fee
                            }
                        }
                    ]
                    # Scrivi l'aggiornamento su InfluxDB
        self.client.write_points(json_body,time_precision='s', database=self.influx_stats,)
        print(f"Updated sensor {sensor_id} in stats db.")

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        # Un nuovo messaggio viene ricevuto
        print(f"Topic: '{msg.topic}', QoS: '{msg.qos}', Message: '{msg.payload.decode()}'")
        
        try:
            # Decodifica del payload JSON una prima volta
            decoded_message = msg.payload.decode()
            print(f"Decoded message (first decode): {decoded_message}")

            # Decodifica ricorsiva fino a ottenere un dizionario o una lista
            final_data = self.recursive_json_decode(decoded_message)
            print(f"Final decoded message: {final_data}")
            print(f"Data type after final decode: {type(final_data)}")

            # Assicurati che 'final_data' sia un dizionario
            if isinstance(final_data, dict):
                data = final_data
                event = data.get('e', [])[0]
                print(f"Extracted event: {event}")

                # Estrai i dettagli dell'evento
                sensor_id = event.get('sensor_id', '')
                status = event.get('v', 'unknown')  # Recupera lo stato
                if status == 'free':
                    self.update_stats_db(event)
                location = event.get('location', 'unknown')
                sensor_type = event.get('type', 'unknown')
                booking_code = event.get('booking_code', '')

                # Controlla se un sensore con lo stesso ID esiste già nel database
                check_query = f'SELECT * FROM "status" WHERE "ID" = \'{sensor_id}\''
                result = self.client.query(check_query)
                
                if list(result.get_points()):
                    # Se il sensore esiste, aggiorna lo stato nel database InfluxDB
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    json_body = [
                        {
                            "measurement": 'status',
                            "tags": {
                                "ID": sensor_id,
                                "type": sensor_type,
                                "location": location
                            },
                            "time": str(current_time),  # Timestamp corrente
                            "fields": {
                                "name": data['bn'],  # Nome del sensore o dispositivo
                                "status": status,  # Stato aggiornato dal messaggio MQTT (es. 'occupied')
                                "booking_code": booking_code  # Codice di prenotazione
                            }
                        }
                    ]
                    # Scrivi l'aggiornamento su InfluxDB
                    self.client.write_points(json_body, time_precision='s', database=self.influx_db)
                    print(f"Updated sensor {sensor_id} status to {status}.")
                else:
                    print(f"Sensor with ID {sensor_id} not found in the database.")
            else:
                print(f"Final data is not a dictionary: {type(final_data)}")
            
                
                
        
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        
        except Exception as e:
            print(f"Error processing message: {e}")








    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, *uri, **params):
        if len(uri) == 0:
            raise cherrypy.HTTPError(400, "Endpoint not specified")
        
        if uri[0] == 'register_device':
            try:
                device_info = cherrypy.request.json
                required_fields = ['ID', 'name', 'type', 'location']
                
                # Verifica che tutti i campi richiesti siano presenti
                for field in required_fields:
                    if field not in device_info:
                        return {"error": f"Missing field: {field}"}, 400
                
                # Controlla se un sensore con lo stesso ID esiste già
                check_query = f'SELECT * FROM "status" WHERE "ID" = \'{device_info["ID"]}\''
                result = self.client.query(check_query)
                
                # Se il risultato non è vuoto, significa che il dispositivo esiste già
                if list(result.get_points()):
                    return {"message": f"Device with ID {device_info['ID']} already exists."}, 409  # Conflict
                
                # Se non esiste, inserisci il nuovo dispositivo
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                json_body = [
                    {
                        "measurement": 'status',
                        "tags": {
                            "ID": str(device_info['ID']),
                            "type": device_info['type'],
                            "location": device_info['location']
                        },
                        "time": str(current_time),  # Timestamp corrente
                        "fields": {
                            "name": device_info['name'],
                            "status": "free",  # Lo stato è forzato a "free"
                            "booking_code": device_info.get('booking_code', '')
                        }
                    }
                ]
                # Scrivi i dati su InfluxDB
                self.client.write_points(json_body, database= self.influx_db)
                print(f"Registered device with ID {device_info['ID']} on InfluxDB.")
                return {"message": f"Device with ID {device_info['ID']} registered successfully."}, 201
            
            except Exception as e:
                print(f"Error registering device: {e}")
                return {"error": str(e)}, 500
            
        if uri[0] == 'reservation':
            try:
                device_info = cherrypy.request.json
                required_fields = ['ID', 'name', 'type', 'location']
                
                # Verifica che tutti i campi richiesti siano presenti
                for field in required_fields:
                    if field not in device_info:
                        return {"error": f"Missing field: {field}"}, 400
                
                # Controlla se un sensore con lo stesso ID esiste già
                check_query = f'SELECT * FROM "status" WHERE "ID" = \'{device_info["ID"]}\''
                result = self.client.query(check_query)
                
                # Se il risultato non è vuoto, significa che il dispositivo esiste già
                if not list(result.get_points()):
                    return {"message": f"Device with ID {device_info['ID']} doesn't exist."}, 409  # Conflict
                
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                json_body = [
                    {
                        "measurement": 'status',
                        "tags": {
                            "ID": str(device_info['ID']),
                            "type": device_info['type'],
                            "location": device_info['location']
                        },
                        "time": str(current_time),  # Timestamp corrente
                        "fields": {
                            "name": device_info['name'],
                            "status": "reserved",  # Lo stato è forzato da "free"
                            "booking_code": device_info.get('booking_code', '')
                        }
                    }
                ]
                # Scrivi i dati su InfluxDB
                self.client.write_points(json_body, database = self.influx_db)
                print(f"Device with ID {device_info['ID']} is reserved on InfluxDB.")
                return {"message": f"Device with ID {device_info['ID']} is reserved."}, 201
            
            except Exception as e:
                print(f"Error registering device: {e}")
                return {"error": str(e)}, 500

        if uri[0] == 'update_device':
            try:
                device_info = cherrypy.request.json
                required_fields = ['ID', 'status', 'last_update', 'booking_code']

                # Check for required fields
                for field in required_fields:
                    if field not in device_info:
                        return {"error": f"Missing field: {field}"}, 400

                sensor_id = device_info['ID']
                status = device_info['status']
                last_update = device_info['last_update']
                booking_code = device_info['booking_code']

                # Update or insert the device status in InfluxDB
                json_body = [
                    {
                        "measurement": 'status',
                        "tags": {
                            "ID": sensor_id
                        },
                        "time": last_update,  # Use the provided timestamp
                        "fields": {
                            "status": status,
                            "booking_code": booking_code
                        }
                    }
                ]
                # Write the update to InfluxDB
                self.client.write_points(json_body, database= self.influx_db)
                print(f"Updated device {sensor_id} status to {status}.")
                return {"message": f"Device {sensor_id} updated successfully."}, 200
            
            except Exception as e:
                print(f"Error updating device: {e}")
                return {"error": str(e)}, 500

        else:
            raise cherrypy.HTTPError(404, "Endpoint not found")
        





    def GET(self, *uri, **params):
        if len(uri) == 0:
            try:
                # Esegui una query per ottenere tutti i sensori dal database
                query = query = 'SELECT LAST("status") AS "status", "ID", "type", "location", "name", "time", "booking_code" FROM "status" GROUP BY "ID"'
                result = self.client.query(query)
                
                # Converti il risultato in un formato JSON-friendly
                sensors = []
                for sensor in result.get_points():
                    sensors.append({
                        'ID': sensor['ID'],
                        'type': sensor['type'],
                        'location': sensor['location'],
                        'name': sensor['name'],
                        'status': sensor['status'],
                        'time':sensor['time'],
                        'booking_code': sensor.get('booking_code', '')
                    })
                
                if not sensors:
                    sensors = {"message": "No sensors found in the database"}
                
                # Converti la lista in una stringa JSON
                return json.dumps(sensors).encode('utf-8')
            
            except Exception as e:
                error_message = {"error": str(e)}
                return json.dumps(error_message).encode('utf-8')
        else:
            raise cherrypy.HTTPError(404, "Endpoint not found")

    


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