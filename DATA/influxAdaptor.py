from datetime import datetime
from pathlib import Path
import paho.mqtt.client as PahoMQTT
import time
import json
from datetime import datetime
from influxdb import InfluxDBClient
import sys
import cherrypy
import requests  
import threading
P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'

class dbAdaptor:
    exposed = True  # Esponi la classe per CherryPy

    def __init__(self, settings):
        #influx_host='localhost', influx_port=8086, influx_user='root', influx_password='root', 
        #        influx_db='IoT_Smart_Parking', influx_stats = 'IoT_SP_Stats'
        
        self.influx_stats = settings["statsDB"]
        self.influx_db = settings["mainDB"]

        self.pubTopic = settings["baseTopic"]
        self.catalog_address = settings['catalog_url']
        self.messageBroker = settings["messageBroker"]
        self.port = settings["brokerPort"]
        self.serviceInfo = settings['serviceInfo']
        self.serviceID = self.serviceInfo['ID']
        self.updateInterval = settings["updateInterval"]
        self.influx_port = settings["influxPort"]

        # Crea un'istanza di paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client()



        # Registra i callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

        # if topic is None:
        #     self.topic = 'ParkingLot/+/status'
        # else:
        #     self.topic = topic


        # Configurazione del client InfluxDB
        self.client = InfluxDBClient(host="localhost", port=self.influx_port, username="root", password="root", database=self.influx_db)
        if {'name': self.influx_db} not in self.client.get_list_database():
            self.client.create_database(self.influx_db)
        if {'name': self.influx_stats} not in self.client.get_list_database():
            self.client.create_database(self.influx_stats)

    def start(self):
        """Start the MQTT client."""
        try:
            # Connect to MQTT broker
            self._paho_mqtt.connect(self.messageBroker, self.port)
            self._paho_mqtt.loop_start()
            print(f"Publisher connected to broker {self.messageBroker}:{self.port}")
            
            # Register the service using a POST request
            self.register_service()

            # Start periodic alive messages
            self.start_periodic_updates()

            self._paho_mqtt.subscribe('ParkingLot/+/status', 2)
            
            

        except Exception as e:
            print(f"Error starting MQTT client: {e}")

    def stop(self):
        """Stop the MQTT client."""
        try:
            self._paho_mqtt.loop_stop()
            self._paho_mqtt.disconnect()
            print("MQTT client stopped.")
        except Exception as e:
            print(f"Error stopping MQTT client: {e}")
    
    def myOnConnect(self, paho_mqtt, userdata, flags, reasonCode, properties=None):
        print(f"Connected to {self.messageBroker} with result code: {reasonCode}")


    def register_service(self):
        """Registers the service in the catalog using POST the first time."""
        # Initial POST request to register the service
        url = f"{self.catalog_address}/services"
        response = requests.post(url, json=self.serviceInfo)
        if response.status_code == 200:
            self.is_registered = True
            print(f"Service {self.serviceID} registered successfully.")
        else:
            print(f"Failed to register service: {response.status_code} - {response.text}")

    def start_periodic_updates(self):
        """
        Starts a background thread that publishes periodic updates via MQTT.
        """
        def periodic_update():
            time.sleep(10)  # Initial delay before sending updates
            while True:
                try:
                    message = {
                        "bn": "updateCatalogService",
                        "e": [
                            {
                                "n": f"{self.serviceID}",
                                "u": "IP",
                                "t": str(time.time()),
                                "v": "alive"
                            }
                        ]
                    }
                    topic = f"ParkingLot/alive/{self.serviceID}"
                    self._paho_mqtt.publish(topic, json.dumps(message))
                    print(f"Published alive message to {topic}: {message}")
                    time.sleep(self.updateInterval)  # Wait before the next update
                except Exception as e:
                    print(f"Error during periodic update: {e}")

        # Start periodic updates in a background thread
        update_thread = threading.Thread(target=periodic_update, daemon=True)
        update_thread.start()

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
        self.client.write_points(json_body,time_precision='s', database=self.influx_stats)
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







    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
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
            
        if uri[0] == 'reservation_exp':
            try:
                device_info = cherrypy.request.json
                required_fields = ['ID', 'name', 'type', 'location', 'booking_code']
                
                # Verifica che tutti i campi richiesti siano presenti
                for field in required_fields:
                    if field not in device_info:
                        return {"error": f"Missing field: {field}"}, 400
                
                # Verifica l'ultima entry per il dispositivo con ID e booking_code specifico
                check_query = f'''
                SELECT * FROM "status" 
                WHERE "ID" = '{device_info["ID"]}' AND "booking_code" = '{device_info["booking_code"]}'
                ORDER BY time DESC LIMIT 1
                '''
                result = self.client.query(check_query)
                
                # Se non ci sono risultati, significa che non c'è nessuna prenotazione attiva con quel booking_code
                points = list(result.get_points())
                if not points:
                    return {"message": f"Device with ID {device_info['ID']} and booking_code {device_info['booking_code']} doesn't exist."}, 409  # Conflict
                
                # Controlla se lo stato dell'ultima entry è "reserved"
                last_entry = points[0]
                if last_entry['status'] != 'reserved':
                    return {"message": "Reservation has already expired or was never made."}, 200  # Nessuna azione necessaria
                
                # Se l'ultima entry è "reserved", continua ad aggiornare lo stato
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
                self.client.write_points(json_body, database=self.influx_db)
                print(f"Device with ID {device_info['ID']} is again free on InfluxDB.")
                return {"message": f"Device with ID {device_info['ID']} is again free."}, 201
            
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
            
        elif uri[0] == 'get_booking_info':
            try:
                request_data = cherrypy.request.json
                booking_code = request_data.get('booking_code')

                if not booking_code:
                    return {"error": "Missing 'booking_code' in request"}, 400

                # Query per sommare la durata e la tariffa totali per il booking_code
                query = f"""
                    SELECT SUM("duration") AS total_duration, SUM("fee") AS total_fee
                    FROM "status"
                    WHERE "booking_code" = '{booking_code}'
                """
                result = self.client.query(query, database=self.influx_stats)

                
                points = list(result.get_points())
                 

                if not points or (points[0]['total_duration'] is None and points[0]['total_fee'] is None):
                    return {"message": f"No data found for booking_code {booking_code}"}, 404

                
                first_point = points[0]

                total_duration = first_point.get('total_duration', 0)
                total_fee = first_point.get('total_fee', 0)

                response = {
                    "booking_code": booking_code,
                    "total_duration": total_duration,
                    "total_fee": total_fee
                }

                return response  

            except Exception as e:
                print(f"Error retrieving booking info: {e}")
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

    settings = json.load(open(SETTINGS))
    test = dbAdaptor(settings)
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
        'server.socket_port': 5001,
        'engine.autoreload.on': False
    })

    # Monta il servizio su /
    cherrypy.tree.mount(test, '/', config)
    
    try:
        cherrypy.engine.start()
        print("dbAdaptor service started on port 5001.")
        cherrypy.engine.block()
    except KeyboardInterrupt:
        print("Shutting down dbAdaptor service...")
    finally:
        test.stop()
        cherrypy.engine.exit()