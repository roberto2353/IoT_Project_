import cherrypy
import json
import time

def addDevice(catalog, devicesInfo):
    catalog["devices"].append(devicesInfo)

def updateDevice(catalog, deviceID, devicesInfo):
    for i in range(len(catalog["devices"])):
        device = catalog["devices"][i]
        if device['ID'] == deviceID:
            catalog["devices"][i] = devicesInfo

def removeDevices(catalog, deviceID):
    for i in range(len(catalog["devices"])):
        device = catalog["devices"][i]
        if device['ID'] == int(deviceID):
            catalog["devices"].pop(i)


class CatalogREST(object):
    exposed = True

    def __init__(self, catalog_address):
        self.catalog_address = catalog_address
    
    def GET(self, *uri, **params):
        catalog=json.load(open(self.catalog_address,"r"))
        if len(uri)==0:#An error will be raised in case there is no uri 
           raise cherrypy.HTTPError(status=400, message='UNABLE TO MANAGE THIS URL')
        elif uri[0]=='all':
            output = catalog
        elif uri[0]=='devices':
            output = {"devices":catalog["devices"]}
        return json.dumps(output)

    def POST(self, *uri, **params):
        catalog=json.load(open(self.catalog_address,"r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        if uri[0]=='devices':
            if not any(d['ID'] == json_body['ID'] for d in catalog["devices"]):
                last_update = time.time()
                json_body['last_update'] = last_update
                addDevice(catalog, json_body)
                output = f"Device with ID {json_body['ID']} has been added"
                print(output)
            else:
                raise cherrypy.HTTPError(status=400, message='DEVICE ALREADY REGISTERED')
  
        json.dump(catalog,open(self.catalog_address,"w"),indent=4)
        print(catalog)
        return output


    def PUT(self, *uri, **params):
        catalog=json.load(open(self.catalog_address,"r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        if uri[0]=='devices':
            if not any(d['ID'] == json_body['ID'] for d in catalog["devices"]):
                raise cherrypy.HTTPError(status=400, message='DEVICE NOT FOUND')
            else:
                last_update = time.time()
                json_body['last_update'] = last_update
                updateDevice(catalog, json_body['ID'], json_body)
        print(catalog)
        json.dump(catalog,open(self.catalog_address,"w"),indent=4)
        return json_body
        
    def DELETE(self, *uri):
        catalog=json.load(open(self.catalog_address,"r"))
        if uri[0]=='devices':
            removeDevices(catalog,uri[1])
            output = f"Device with ID {uri[1]} has been removed"
            print(output)
        json.dump(catalog,open(self.catalog_address,"w"),indent=4)


if __name__ == '__main__':
    catalogClient = CatalogREST("catalog.json")
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.config.update({'server.socket_host': 'localhost', 'server.socket_port': 8080})
    #cherrypy.config.update({'server.socket_port': 8080})
    cherrypy.tree.mount(catalogClient, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
    cherrypy.engine.exit()
