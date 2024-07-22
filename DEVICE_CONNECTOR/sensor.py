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
        threading.Thread.__init__(self)
        self.settings = json.load(open('settings.json'))
        self.catalogURL=self.settings['catalogURL']
        self.devices = self.settings['devices']
        #self.deviceInfo=self.settings['deviceInfo']
        #self.deviceInfo['ID'] = random.randint(1, 1000)
        #self.deviceInfo['commands'] = ['hum', 'temp']
        self.pingInterval = pi
        #requests.post(f'{self.catalogURL}/devices', data=json.dumps(self.deviceInfo))
        self.deviceInfo = {} 
        self.register_devices()
        self.start()

    def register_devices(self):
        for device in self.devices:
            device_info = device['deviceInfo']
            #device_info['ID'] = random.randint(1, 1000)
            device_info['ID'] = SensorREST.devices_counter
            SensorREST.devices_counter += 1 
            if device_info['type'] == 'photocell':
                device_info['commands'] = ['status']
            requests.post(f'{self.catalogURL}/devices', data=json.dumps(device_info))

    def GET(self, *uri, **params):
        if len(uri) != 0:
            if uri[0] == 'status':
                value = random.randint(0, 500)
            #if uri[0] == 'temp':
                #value = random.randint(10, 25)
            output = {'deviceID': self.deviceInfo['ID'], str(uri[0]): value}
            return json.dumps(output)
        else:
            return json.dumps(self.deviceInfo)

    def run(self):
        while True:
            time.sleep(self.pingInterval)
            self.pingCatalog()
    
    def pingCatalog(self):
        for device_id, device_info in self.deviceInfo.items():
            requests.put(f'{self.catalogURL}/devices', data=json.dumps(device_info))


if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    s = SensorREST(5)
    cherrypy.config.update({'server.socket_host': 'localhost', 'server.socket_port': 8081})
    #cherrypy.config.update({'server.socket_port': 9090})
    cherrypy.tree.mount(s, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
    cherrypy.engine.exit()
