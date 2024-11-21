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
        self.influx_prova = settings["provaDB"]

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
        #     self.topic = 'ParkingLotFabio/+/status'
        # else:
        #     self.topic = topic

        #self.messageBroker = 'localhost'

        # Configurazione del client InfluxDB
        self.client = InfluxDBClient(host="localhost", port=self.influx_port, username="root", password="root", database=self.influx_db)
        if {'name': self.influx_db} not in self.client.get_list_database():
            self.client.create_database(self.influx_db)
        if {'name': self.influx_stats} not in self.client.get_list_database():
            self.client.create_database(self.influx_stats)
        if {'name': self.influx_prova} not in self.client.get_list_database():
            self.client.create_database(self.influx_prova)

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
            self._paho_mqtt.subscribe('ParkingLotFabio/+/status', 2)
            
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
                    topic = f"ParkingLotFabio/alive/{self.serviceID}"
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
        parking = data.get('parking')
        booking_code = data.get('booking_code', 'unknown')
        duration = data.get('duration')
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sensor_id = data.get('sensor_id')
        active = data.get('active')
        json_body = [
                        {
                            "measurement": 'status',
                            "tags": {
                                "ID": sensor_id,
                                "parking_id": parking,
                                "floor": floor
                            },
                            "time": str(current_time),  # Timestamp corrente
                            "fields": {
                                "booking_code": booking_code,  # Codice di prenotazione
                                "duration": float(duration),
                                "fee": float(fee),
                                "active": active
                            }
                        }
                    ]
        # TODO NON FUNZIONA
        print(f"\n\n\nDOVREBBE STAMPARE LA FEE = {float(fee)} E LA DURATION = {float(duration)}. DATA TYPE: {type(fee)}\n\n\n")
                    # Scrivi l'aggiornamento su InfluxDB
        self.client.write_points(json_body,time_precision='s', database=self.influx_prova) #influx_stats
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
                
                if status == 'free' and event.get('flag', '') != True:
                    self.update_stats_db(event)
                location = event.get('location', 'unknown')
                sensor_type = event.get('type', 'unknown')
                booking_code = event.get('booking_code', '')
                active = event.get('active', '') 
                parking = event.get('parking', 'unknown')

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
                                "parking_id": parking,
                                "type": sensor_type,
                                "location": location
                            },
                            "time": str(current_time),  # Timestamp corrente
                            "fields": {
                                "name": data['bn'],  # Nome del sensore o dispositivo
                                "status": status,  # Stato aggiornato dal messaggio MQTT (es. 'occupied')
                                "booking_code": booking_code,  # Codice di prenotazione
                                "active": active
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
                required_fields = ['ID', 'name', 'type', 'location', 'active', 'parking']
                
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
                            "parking_id": device_info['parking'],
                            "type": device_info['type'],
                            "location": device_info['location']
                        },
                        "time": str(current_time),  # Timestamp corrente
                        "fields": {
                            "name": device_info['name'],
                            "status": "free",  # Lo stato è forzato a "free"
                            "booking_code": device_info.get('booking_code', ''),
                            "active": device_info['active'] 
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
                required_fields = ['ID', 'name', 'type', 'location', 'booking_code', 'parking']
                
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
                            "parking_id": device_info['parking'],
                            "type": device_info['type'],
                            "location": device_info['location']
                        },
                        "time": str(current_time),  # Timestamp corrente
                        "fields": {
                            "name": device_info['name'],
                            "status": "free",  # Lo stato è forzato a "free"
                            "booking_code": device_info.get('booking_code', ''),
                            "active": device_info['active']
                        }
                    }
                ]
                # Scrivi i dati su InfluxDB
                self.client.write_points(json_body, database=self.influx_db)
                event = {
                    "n": f"{str(device_info['ID'])}/status", 
                    "u": "boolean", 
                    #"t": str(datetime.datetime.now()), 
                    "v": "free",  # Cambiamo lo stato in 'free'
                    "sensor_id": device_info['ID'],
                    "location": device_info['location'],
                    "type": device_info['type'],
                    "booking_code": device_info.get('booking_code', ''),
                    "active": device_info.get('active', '')
                    #"floor": self.extract_floor(selected_device['location'])
                    }
            
                message = {"bn": device_info['name'], "e": [event]}
                mqtt_topic_dc = f"{self.pubTopic}/{device_info['name_dev']}/{str(device_info['ID'])}/status"
                self._paho_mqtt.publish(mqtt_topic_dc, json.dumps(message))
                print(f"Messaggio pubblicato su topic per il DC scadenza prenotazione")

                print(f"Device with ID {device_info['ID']} is again free on InfluxDB.")

                return {"message": f"Device with ID {device_info['ID']} is again free."}, 201
            
            except Exception as e:
                print(f"Error registering device: {e}")
                return {"error": str(e)}, 500

        if uri[0] == 'update_device':
            try:
                device_info = cherrypy.request.json
                required_fields = ['ID', 'status', 'last_update', 'booking_code','active']

                # Check for required fields
                for field in required_fields:
                    if field not in device_info:
                        return {"error": f"Missing field: {field}"}, 400

                sensor_id = device_info['ID']
                status = device_info['status']
                last_update = device_info['last_update']
                booking_code = device_info['booking_code']
                active = device_info['active']

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
                            "booking_code": booking_code,
                            "active": active
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

                # Query per ottenere tutte le transazioni individuali per il booking_code
                query_transactions = f"""
                    SELECT "slot_id", "duration", "fee", time
                    FROM "status"
                    WHERE "booking_code" = '{booking_code}'
                """
                result_transactions = self.client.query(query_transactions, database=self.influx_prova)

                transactions = []
                for point in result_transactions.get_points():
                    transactions.append({
                        "slot_id": point.get("slot_id", "N/A"),
                        "duration": point.get("duration", 0),
                        "fee": point.get("fee", 0),
                        "time": point.get("time")  # Facoltativo: data/ora
                    })

                # Controlla se ci sono transazioni
                if not transactions:
                    return {"message": f"No transactions found for booking_code {booking_code}"}, 404

                # Risposta solo con transazioni individuali
                response = {
                    "booking_code": booking_code,
                    "transactions": transactions
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
                # Esegui una query per ottenere ultimo stato di tutti i sensori dal database
                query = 'SELECT LAST("status") AS "status", "ID", "type", "location", "name", "parking_id", "time", "booking_code", "active" FROM "status" GROUP BY "ID"'
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
                        'booking_code': sensor.get('booking_code', ''),
                        'active': sensor.get('active', ''),
                        "parking_id": sensor.get('parking_id', '')
                    })
                
                if not sensors:
                    sensors = {"message": "No sensors found in the database"}
                
                # Converti la lista in una stringa JSON
                print("returned sensors from db via adaptor")
                return json.dumps(sensors).encode('utf-8')
            
            except Exception as e:
                error_message = {"error": str(e)}
                return json.dumps(error_message).encode('utf-8')

        elif len(uri) >= 2 and uri[0] == "sensors" and uri[1] == "occupied":
            start = params.get('start')
            end = params.get('end')
            parking_id = params.get('parking_id')
            return self.get_occupied_sensors_by_time(start, end, parking_id)
        
        elif uri[0] == "sensors" and len(uri) == 1:
            # Endpoint to get all sensor data, with optional time range
            start = params.get('start')
            end = params.get('end')
            parking_id = params.get('parking_id')
            return self.get_all_sensors(start, end, parking_id)

        elif len(uri) == 2 and uri[0] == "sensors":
            # Endpoint to get sensor data by ID
            sensor_id = uri[1]
            parking_id = params.get('parking_id')
            return self.get_sensor_by_id(sensor_id, parking_id)
        
        elif len(uri) == 1 and uri[0] == "fees":
            start = params.get('start')
            end = params.get('end')
            parking_id = params.get('parking_id')
            return self.get_fees(start, end, parking_id)

        elif len(uri) ==1 and uri[0] == "durations":
            start = params.get('start')
            end = params.get('end')
            parking_id = params.get('parking_id')
            return self.get_durations(start, end, parking_id)
        
        else:
            raise cherrypy.HTTPError(404, "Endpoint not found")

    def get_fees(self, start=None, end=None, parking_id=None):
        try:
            query = 'SELECT ID, time, booking_code, fee FROM "status"'
            if start and end:
                query += f' WHERE time >= {start} AND time <= {end}'
            elif start:
                query += f' WHERE time >= {start}'
            elif end:
                query += f' WHERE time <= {end}'
            if parking_id:
                query += f' AND parking_id = \'{parking_id}\''
            
            query += ' GROUP BY "ID"'
            result = self.client.query(query, database = 'prova_stats')
            #print(result)
            sensors = []
            sensors = list(result.get_points())
            if not sensors:
                return json.dumps({"message": "No data found in the database for the specified time range"}).encode('utf-8')
            #print(sensors)
            return json.dumps(sensors).encode('utf-8')

        except Exception as e:
            error_message = {"error": str(e)}
            return json.dumps(error_message).encode('utf-8')
    
    def get_durations(self, start=None, end=None, parking_id=None):
        try:
            query = 'SELECT ID, time, booking_code, "duration" FROM "status"'
            if start and end:
                query += f' WHERE time >= {start} AND time <= {end}'
            elif start:
                query += f' WHERE time >= {start}'
            elif end:
                query += f' WHERE time <= {end}'
            if parking_id:
                query += f' AND parking_id = \'{parking_id}\''
            
            query += ' GROUP BY "ID"'
            result = self.client.query(query, database = 'prova_stats')
            #print(result)
            sensors = []
            sensors = list(result.get_points())
            print(sensors)
            if not sensors:
                return json.dumps({"message": "No data found in the database for the specified time range"}).encode('utf-8')
            #print(sensors)
            return json.dumps(sensors).encode('utf-8')

        except Exception as e:
            error_message = {"error": str(e)}
            return json.dumps(error_message).encode('utf-8')

    def get_all_sensors(self, start=None, end=None, parking_id=None):
        try:
            # Base query to get the latest status for all sensors
            query = 'SELECT * FROM "status"'

            # Modify query if start and end times are provided
            if start and end:
                query += f' WHERE time >= {start} AND time <= {end}'
            elif start:
                query += f' WHERE time >= {start}'
            elif end:
                query += f' WHERE time <= {end}'
            if parking_id:
                query += f' AND parking_id = \'{parking_id}\''
            
            query += ' GROUP BY "ID"'

            result = self.client.query(query)
            #print(result)
            sensors = []
            sensors = list(result.get_points())
            
            

            if not sensors:
                return json.dumps({"message": "No sensors found in the database for the specified time range"}).encode('utf-8')
            #print(sensors)
            return json.dumps(sensors).encode('utf-8')

        except Exception as e:
            error_message = {"error": str(e)}
            return json.dumps(error_message).encode('utf-8')

    def get_occupied_sensors_by_time(self, start, end, parking_id=None):
        try:
            query = f'SELECT * FROM "status" WHERE "status" = \'occupied\' AND time >= {start} AND time <= {end}'
            if parking_id:
                query += f' AND parking_id = \'{parking_id}\''
            result = self.client.query(query)
            
            occupied_sensors = []
            occupied_sensors = list(result.get_points())
            
            if not occupied_sensors:
                return json.dumps({"message": "No occupied sensors found in the specified time range"}).encode('utf-8')
            
            return json.dumps(occupied_sensors).encode('utf-8')

        except Exception as e:
            error_message = {"error": str(e)}
            return json.dumps(error_message).encode('utf-8')
    
    def get_sensor_by_id(self, sensor_id, parking_id=None):
        try:
            query = f'SELECT * FROM "status" WHERE "ID" = \'{sensor_id}\''
            if parking_id:
                query += f' AND parking_id = \'{parking_id}\''
                
            result = self.client.query(query)
            
            sensors = []
            sensors = list(result.get_points())
            
            if not sensors:
                return json.dumps({"message": f"No data found for sensor ID {sensor_id}"}).encode('utf-8')
            
            return json.dumps(sensors).encode('utf-8')

        except Exception as e:
            error_message = {"error": str(e)}
            return json.dumps(error_message).encode('utf-8')

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