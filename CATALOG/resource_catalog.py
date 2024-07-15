import cherrypy
import json
import os
from datetime import datetime

# Percorso del file JSON
JSON_FILE = 'resource_catalog.json'

def read_json():
    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'w') as f:
            json.dump({
                "projectOwner": "IoTGroup8",
                "projectName": "Iot4SmartParking",
                "lastUpdate": str(datetime.now()),
                "broker": {
                    "IP": "test.mosquitto.org",
                    "port": 1883
                },
                "devicesList": []
            }, f)
    with open(JSON_FILE, 'r') as f:
        return json.load(f)

def write_json(data):
    data["lastUpdate"] = str(datetime.now())
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)


class ResourceCatalogAPI:
    
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def GET(self, resource_type=None, id=None):
        data = read_json()
        if resource_type == "devicesList":
            if id:
                id = int(id)
                device = next((device for device in data['devicesList'] if device['id'] == id), None)
                if device:
                    return device
                else:
                    cherrypy.response.status = 404
                    return {"error": "Device not found"}
            else:
                return data['devicesList']
        else:
            return data

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, resource_type):
        if resource_type != "devicesList":
            cherrypy.response.status = 404
            return {"error": "Resource type not found"}
        
        data = cherrypy.request.json
        catalog = read_json()
        new_id = max([device['id'] for device in catalog['devicesList']], default=0) + 1
        new_device = {"id": new_id, **data}
        
        catalog['devicesList'].append(new_device)
        write_json(catalog)
        cherrypy.response.status = 201
        return new_device

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self, resource_type, id):
        if resource_type != "devicesList":
            cherrypy.response.status = 404
            return {"error": "Resource type not found"}
        
        id = int(id)
        data = cherrypy.request.json
        catalog = read_json()
        device = next((device for device in catalog['devicesList'] if device['id'] == id), None)
        
        if device:
            device.update(data)
            write_json(catalog)
            return device
        else:
            cherrypy.response.status = 404
            return {"error": "Device not found"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def DELETE(self, resource_type, id):
        if resource_type != "devicesList":
            cherrypy.response.status = 404
            return {"error": "Resource type not found"}
        
        id = int(id)
        catalog = read_json()
        device = next((device for device in catalog['devicesList'] if device['id'] == id), None)
        
        if device:
            catalog['devicesList'].remove(device)
            write_json(catalog)
            cherrypy.response.status = 204
            return {}
        else:
            cherrypy.response.status = 404
            return {"error": "Device not found"}


if __name__ == '__main__':
    cherrypy.tree.mount(ResourceCatalogAPI(), '/catalog', {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')],
        }
    })
    cherrypy.config.update({
        'server.socket_host': '127.0.0.1',
        'server.socket_port': 8080,
        'engine.autoreload.on': True
    })
    cherrypy.engine.start()
    cherrypy.engine.block()
