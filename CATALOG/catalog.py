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

SERVICE_EXPIRATION_THRESHOLD = 180  # Every 3 minutes old services are removed
DEVICE_EXPIRATION_THRESHOLD = 120 #Every 2 minutes
# Class to manage the catalog operations (loading, updating, saving)
class CatalogManager:
    def __init__(self, catalog_file):
        self.catalog_file = catalog_file
        self.reset_catalog()
        self.catalog=self.load_catalog()

        self.expiration_thread_services = threading.Thread(target=self.run_service_expiration_check, daemon=True)
        self.expiration_thread_devices = threading.Thread(target=self.run_device_expiration_check, daemon=True)
        self.expiration_thread_services.start()
        self.expiration_thread_devices.start()

    def load_catalog(self):
        """Load the catalog from a JSON file."""
        try:
            with open(self.catalog_file, 'r') as file:
                return(json.load(file))
                
        except Exception as e:
            print(f"Failed to load catalog: {e}")

    def write_catalog(self):
        """Save the catalog to the JSON file."""
        try:
            with open(self.catalog_file, 'w') as file:
                json.dump(self.catalog, file, indent=4)
        except Exception as e:
            print(f"Failed to save catalog: {e}")
    
    def reset_catalog(self):
        with open(self.catalog_file, 'r') as f:
            catalog = json.load(f)
        catalog['devices'] = []
        catalog['users'] = []
        catalog['parkings'] = []
        catalog['services'] = []
        with open(self.catalog_file, 'w') as file:
            json.dump(catalog, file, indent=4)
        print(f"Catalog is starting...")

    # Catalog manipulation methods
    def add_device(self, devices_info):
        if not any(d['ID'] == devices_info['ID'] for d in self.catalog["devices"]):
            self.catalog["devices"].append(devices_info)
            self.write_catalog()
        else:
            raise ValueError(f"Device with ID {devices_info['ID']} already exists")

    def update_device(self, device_id, devices_info):
        for device in self.catalog["devices"]:
            if device['ID'] == device_id:
                device.update(devices_info)
                self.write_catalog()
                return
        raise ValueError(f"Device with ID {device_id} not found")

    def remove_device(self, device_id):
        for i, device in enumerate(self.catalog["devices"]):
            if device['ID'] == device_id:
                self.catalog["devices"].pop(i)
                self.write_catalog()
                return
        raise ValueError(f"Device with ID {device_id} not found")

    def add_service(self, service_info):
    # Check if the service ID already exists in the catalog
        if any(service['ID'] == service_info['ID'] for service in self.catalog["services"]):
            raise ValueError(f"Service with ID {service_info['ID']} already exists.")
    
        self.catalog["services"].append(service_info)
        self.write_catalog()
        return f"Service with ID {service_info['ID']} added successfully."


    def update_service(self, service_id, service_info):
    # Check if the service exists before updating
        for i, service in enumerate(self.catalog["services"]):
            if service['ID'] == service_id:
                self.catalog["services"][i] = service_info
                self.write_catalog()
                return f"Service with ID {service_id} updated successfully."
    
        raise ValueError(f"Service with ID {service_id} not found.")


    def remove_service(self, service_id):
    # Check if the service exists before removing
        for i, service in enumerate(self.catalog["services"]):
            if service['ID'] == service_id:
                self.catalog["services"].pop(i)
                self.write_catalog()
                return f"Service with ID {service_id} removed successfully."
    
        raise ValueError(f"Service with ID {service_id} not found.")


    def add_user(self, user_info):
        self.catalog["users"].append(user_info)
        self.write_catalog()

    def update_user(self, user_id, user_info):
        for i, user in enumerate(self.catalog["users"]):
            if user['ID'] == user_id:
                self.catalog["users"][i] = user_info
                self.write_catalog()
                return

    def remove_user(self, user_id):
        self.catalog["users"] = [u for u in self.catalog["users"] if u['ID'] != user_id]
        self.write_catalog()

    def add_parking(self, parking_info):
        self.catalog["parkings"].append(parking_info)
        self.write_catalog()

    def update_parking(self, parking_id, parking_info):
        for i, parking in enumerate(self.catalog["parkings"]):
            if parking['ID'] == parking_id:
                self.catalog["parkings"][i] = parking_info
                self.write_catalog()
                return

    def remove_parking(self, parking_id):
        self.catalog["parkings"] = [p for p in self.catalog["parkings"] if p['ID'] != parking_id]
        self.write_catalog()

    def check_service_expiration(self):
        """Remove services that have expired based on their 'last_updated' timestamp."""
        current_time = time.time()
        updated_services = [
            s for s in self.catalog["services"]
            if s.get("last_updated") and (current_time - float(s["last_updated"]) <= SERVICE_EXPIRATION_THRESHOLD)
        ]
        self.catalog["services"] = updated_services
        self.write_catalog()
    

    def check_device_expiration(self):
        """Remove devices that have expired based on their 'last_updated' timestamp."""
        current_time = time.time()
        updated_devices = [
        d for d in self.catalog["devices"]
        if d.get("last_update") and (current_time - float(d["last_update"]) <= DEVICE_EXPIRATION_THRESHOLD)
        ]
        self.catalog["devices"] = updated_devices
        self.write_catalog()
        
    def run_service_expiration_check(self):
        """Periodically check and remove expired services."""
        while True:
            self.check_service_expiration()
            time.sleep(SERVICE_EXPIRATION_THRESHOLD)

    def run_device_expiration_check(self):
        """Periodically check and remove expired devices."""
        while True:
            self.check_device_expiration()
            time.sleep(DEVICE_EXPIRATION_THRESHOLD)

# Class for REST API, interacts with CatalogManager
class CatalogREST(object):
    exposed = True

    def __init__(self, catalog_manager):
        self.catalog_manager = catalog_manager

    def GET(self, *uri, **params):
        """Handle GET requests."""
        if len(uri) == 0:
            raise cherrypy.HTTPError(status=400, message='Invalid URL')
        elif uri[0] == 'all':
            return json.dumps(self.catalog_manager.catalog)
        elif uri[0] == 'devices':
            return json.dumps({"devices": self.catalog_manager.catalog["devices"]})
        elif uri[0] == 'services':
            return json.dumps({"services": self.catalog_manager.catalog["services"]})
        elif uri[0] == 'users':
            return json.dumps({"users": self.catalog_manager.catalog["users"]})
        elif uri[0] == 'parkings':
            return json.dumps({"parkings": self.catalog_manager.catalog["parkings"]})
        else:
            raise cherrypy.HTTPError(status=404, message='Resource not found')

    def POST(self, *uri, **params):
        """Handle POST requests to add new entries."""
        try:
            body = cherrypy.request.body.read()
            json_body = json.loads(body.decode('utf-8'))

            if uri[0] == 'devices':
                self.catalog_manager.add_device(json_body)
                return f"Device with ID {json_body['ID']} added"
            elif uri[0] == 'services':
                print("pippo")
                self.catalog_manager.add_service(json_body)
                return f"Service with ID {json_body['ID']} added"
            elif uri[0] == 'users':
                self.catalog_manager.add_user(json_body)
                return f"User with ID {json_body['ID']} added"
            elif uri[0] == 'parkings':
                self.catalog_manager.add_parking(json_body)
                return f"Parking with ID {json_body['ID']} added"
            else:
                raise cherrypy.HTTPError(status=404, message='Resource not found')
        except Exception as e:
            print(f"Error in POST: {e}")
            raise cherrypy.HTTPError(500, 'Internal Server Error')

    def PUT(self, *uri, **params):
        """Handle PUT requests to update existing entries."""
        try:
            body = cherrypy.request.body.read()
            json_body = json.loads(body.decode('utf-8'))

            if uri[0] == 'devices':
                self.catalog_manager.update_device(json_body['ID'], json_body)
                return f"Device with ID {json_body['ID']} updated"
            elif uri[0] == 'services':
                self.catalog_manager.update_service(json_body['ID'], json_body)
                return f"Service with ID {json_body['ID']} updated"
            elif uri[0] == 'users':
                self.catalog_manager.update_user(json_body['ID'], json_body)
                return f"User with ID {json_body['ID']} updated"
            elif uri[0] == 'parkings':
                self.catalog_manager.update_parking(json_body['ID'], json_body)
                return f"Parking with ID {json_body['ID']} updated"
            else:
                raise cherrypy.HTTPError(status=404, message='Resource not found')
        except Exception as e:
            print(f"Error in PUT: {e}")
            raise cherrypy.HTTPError(500, 'Internal Server Error')

    def DELETE(self, *uri):
        """Handle DELETE requests to remove entries."""
        try:
            if uri[0] == 'devices':
                self.catalog_manager.remove_device(uri[1])
                return f"Device with ID {uri[1]} removed"
            elif uri[0] == 'services':
                self.catalog_manager.remove_service(uri[1])
                return f"Service with ID {uri[1]} removed"
            elif uri[0] == 'users':
                self.catalog_manager.remove_user(uri[1])
                return f"User with ID {uri[1]} removed"
            elif uri[0] == 'parkings':
                self.catalog_manager.remove_parking(uri[1])
                return f"Parking with ID {uri[1]} removed"
            else:
                raise cherrypy.HTTPError(status=404, message='Resource not found')
        except Exception as e:
            print(f"Error in DELETE: {e}")
            raise cherrypy.HTTPError(500, 'Internal Server Error')

class MySubscriber:
        def __init__(self, catalog_manager, settings):
            self.clientID = "CatalogSubscriber_roby"
			# create an instance of paho.mqtt.client
            self._paho_mqtt = PahoMQTT.Client(client_id=self.clientID) 
            
			# register the callback
            self._paho_mqtt.on_connect = self.myOnConnect
            self._paho_mqtt.on_message = self.myOnMessageReceived 
            self.pubTopic = "ParkingLot/alive/#"
            self.messageBroker = settings["messageBroker"]
            self.port = settings["brokerPort"]
            self.catalog_manager = catalog_manager

            self.start()

        def start (self):
            #manage connection to broker
            self._paho_mqtt.connect(self.messageBroker, self.port)
            self._paho_mqtt.loop_start()
            # subscribe for a topic
            self._paho_mqtt.subscribe(self.pubTopic, 2)

        def stop (self):
            self._paho_mqtt.unsubscribe(self.pubTopic)
            self._paho_mqtt.loop_stop()
            self._paho_mqtt.disconnect()

        def myOnConnect(self, paho_mqtt, userdata, flags, reasonCode, properties=None):
            print(f"Connected to {self.messageBroker} with result code: {reasonCode}")


        def myOnMessageReceived (self, paho_mqtt , userdata, msg):
            message = json.loads(msg.payload.decode("utf-8")) #{"bn": updateCatalog<>, "e": [{...}]}
            #self.catalog = CatalogREST(self.catalog_manager)
            if message['bn'] == "updateCatalogSlot":            
                self.catalog_manager.update_device(message['e'][0])# {"n": ID, "t": time.time(), "v": "", "u": IP}
                print("Device updated")
            if message['bn'] == "updateCatalogService":            
                self.catalog_manager.update_service(message['e'][0])# {"n": serviceName, "t": time.time(), "v": "", "u": IP}
                print(f"Service {message['e'][0]['n']} updated")

if __name__ == '__main__':
    catalog_manager = CatalogManager("catalog.json")
    catalog_rest = CatalogREST(catalog_manager)

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }

    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8090})
    cherrypy.tree.mount(catalog_rest, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()