import cherrypy
import requests
import uuid
import time
import json
from MyMQTT import MyMQTT
from datetime import datetime


class ParkingService:
    def __init__(self, baseTopic, broker, port):
        self.pubTopic = f"{baseTopic}"
        self.client = MyMQTT("Reservation_Fabio", broker, port, None)
        self.entrance_algorithm_url = "http://127.0.0.1:8081/get_best_parking"
    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    @cherrypy.tools.json_out()
    def book(self):
        try:
            
            response = requests.get(self.entrance_algorithm_url)
            if response.status_code == 200:
                selected_device = response.json().get("parking")
                print(f"selected device for current booking: {selected_device['ID']}")
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if selected_device:
                    # Create a booking code
                    booking_code = str(uuid.uuid4())
                    selected_device['status'] = 'reserved'
                    selected_device['booking_code'] = booking_code
                    selected_device['last_update'] = str(current_time)

                    # Send reservation data to adaptor
                    reservation_url = 'http://127.0.0.1:5000/reservation'
                    headers = {'Content-Type': 'application/json'}
                    reservation_data = {
                        "ID": selected_device['ID'],
                        "name": selected_device.get('name', 'unknown'),
                        "type": selected_device.get('type', 'unknown'),
                        "location": selected_device.get('location', 'unknown'),
                        "booking_code": booking_code
                    }
                    requests.post(reservation_url, headers=headers, json=reservation_data)

                    # Publish MQTT message
                    event = {
                        "n": f"{str(selected_device['ID'])}/status", "u": "boolean", 
                        "t": str(datetime.now()), "v": 'reserved',
                        "sensor_id": selected_device['ID'],
                        "location": selected_device.get('location', 'unknown'),
                        "type": selected_device.get('type', 'unknown'),
                        "booking_code": booking_code
                    }
                    message = {"bn": selected_device['name'], "e": [event]}
                    self.client.myPublish(f"{self.pubTopic}/{selected_device['ID']}/status", message)

                    return {
                        "message": f"Slot {selected_device['location']} successfully booked.",
                        "booking_code": booking_code,
                        "slot_id": selected_device['ID']
                    }
                else:
                    return {"message": "No free slots available"}
            else:
                raise cherrypy.HTTPError(500, 'Error getting parking data')

        except requests.exceptions.RequestException as e:
            cherrypy.log(f"Request error: {str(e)}")
            raise cherrypy.HTTPError(500, 'Error during communication with the parking system')

    def start(self):
        """Start the MQTT client."""
        self.client.start()

    def stop(self):
        """Stop the MQTT client."""
        self.client.stop()

if __name__ == '__main__':
    conf = json.load(open('settings.json'))
    baseTopic = conf["baseTopic"]
    broker = conf["messageBroker"]
    port = conf["brokerPort"]

    res = ParkingService(baseTopic, broker, port)
    res.start()
    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8098})
    cherrypy.quickstart(res)