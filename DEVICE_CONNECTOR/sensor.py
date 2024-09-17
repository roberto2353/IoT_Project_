import cherrypy
import requests
import json
import random
import time
import threading

class SensorREST(threading.Thread):
    exposed = True
    devices_counter = 1

    def __init__(self, pi):
        
        self.settings = json.load(open('settings.json'))
        self.catalogURL = self.settings['catalogURL']
        self.devices = self.settings['devices']
        self.pingInterval = pi
        #self.first_insertion = True
        self.deviceInfo = []  # Initialize as a list to store multiple device infos
        self.register_devices()
        threading.Thread.__init__(self)
        self.start()

    def register_devices(self):
        for device in self.devices:
            device_info = device['deviceInfo']
            device_info['ID'] = SensorREST.devices_counter
            SensorREST.devices_counter += 1
            if device_info['type'] == 'photocell':
                device_info['commands'] = ['status']
            self.deviceInfo.append(device_info)  # Store device info in a list
            requests.post(f'{self.catalogURL}/devices', data=json.dumps(device_info))

    def GET(self, *uri, **params):
        if len(uri) != 0:
            command = uri[0]
            if command == 'status':
                output = []
                for device in self.deviceInfo:
                    if 'status' in device['commands']:
                        #value changes every time i'm doing the get
                        value = random.randint(0, 1)
                        output.append({'deviceID': device['ID'], 'status': value})
                return json.dumps(output)
            else:
                raise cherrypy.HTTPError(status=400, message='COMMAND NOT RECOGNIZED')
        else:
            return json.dumps(self.deviceInfo)

    def run(self):
        while True:
            time.sleep(self.pingInterval)
            self.pingCatalog()
    
    def pingCatalog(self):
        for device in self.deviceInfo:
            device['last_update'] = time.time()
            try:
                response = requests.put(f'{self.catalogURL}/devices', data=json.dumps(device))
                if response.status_code != 200:
                    print(f"Failed to update device {device['ID']}")
            except requests.RequestException as e:
                print(f"Error updating device {device['ID']}: {e}")

if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.config.update({'server.socket_host': 'localhost', 'server.socket_port': 8083})
    s = SensorREST(5)
    cherrypy.tree.mount(s, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()