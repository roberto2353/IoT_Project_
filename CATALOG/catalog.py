import cherrypy
import json
import time
import uuid
# Funzioni per gestire i dispositivi e gli altri elementi del catalogo
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

def add_user(catalog, user_info):
    catalog["users"].append(user_info)

def update_user(catalog, user_id, user_info):
    for i in range(len(catalog["users"])):
        user = catalog["users"][i]
        if user['ID'] == user_id:
            catalog["users"][i] = user_info

def remove_user(catalog, user_id):
    for i in range(len(catalog["users"])):
        user = catalog["users"][i]
        if user['ID'] == user_id:
            catalog["users"].pop(i)
            break

def add_parking(catalog, parking_info):
    catalog["parkings"].append(parking_info)

def update_parking(catalog, parking_id, parking_info):
    for i in range(len(catalog["parkings"])):
        parking = catalog["parkings"][i]
        if parking['ID'] == parking_id:
            catalog["parkings"][i] = parking_info

def remove_parking(catalog, parking_id):
    for i in range(len(catalog["parkings"])):
        parking = catalog["parkings"][i]
        if parking['ID'] == parking_id:
            catalog["parkings"].pop(i)
            break

def add_service(catalog, service_info):
    catalog["services"].append(service_info)

def update_service(catalog, service_id, service_info):
    for i in range(len(catalog["services"])):
        service = catalog["services"][i]
        if service['ID'] == service_id:
            catalog["services"][i] = service_info

def remove_service(catalog, service_id):
    for i in range(len(catalog["services"])):
        service = catalog["services"][i]
        if service['ID'] == service_id:
            catalog["services"].pop(i)
            break

class CatalogREST(object):
    exposed = True

    def __init__(self, catalog_address):
        self.catalog_address = catalog_address
    
    def GET(self, *uri, **params):
        catalog = json.load(open(self.catalog_address, "r"))
        if len(uri) == 0:
            raise cherrypy.HTTPError(status=400, message='UNABLE TO MANAGE THIS URL')
        elif uri[0] == 'all':
            output = catalog
        elif uri[0] == 'devices':
            output = {"devices": catalog["devices"]}
        elif uri[0] == 'services':
            output = {"services": catalog["services"]}
        elif uri[0] == 'users':
            output = {"users": catalog["users"]}
        elif uri[0] == 'parkings':
            output = {"parkings": catalog["parkings"]}
        else:
            raise cherrypy.HTTPError(status=404, message='RESOURCE NOT FOUND')
        return json.dumps(output)

    def POST(self, *uri, **params):
        try:
            catalog = json.load(open(self.catalog_address, "r"))
            body = cherrypy.request.body.read()
            json_body = json.loads(body.decode('utf-8')) if body else {}

            if uri[0] == 'devices':
                if not any(d['ID'] == json_body['ID'] for d in catalog["devices"]):
                    last_update = time.time()
                    json_body['last_update'] = last_update
                    addDevice(catalog, json_body)
                    output = f"Device with ID {json_body['ID']} has been added"
                else:
                    raise cherrypy.HTTPError(400, 'DEVICE ALREADY REGISTERED')

            elif uri[0] == 'services':
                if not any(d['ID'] == json_body['ID'] for d in catalog["services"]):
                    add_service(catalog, json_body)
                    output = f"Service with ID {json_body['ID']} has been added"
                else:
                    raise cherrypy.HTTPError(400, 'SERVICE ALREADY REGISTERED')

            elif uri[0] == 'users':
                if not any(d['ID'] == json_body['ID'] for d in catalog["users"]):
                    add_user(catalog, json_body)
                    output = f"User with ID {json_body['ID']} has been added"
                else:
                    raise cherrypy.HTTPError(400, 'USER ALREADY REGISTERED')

            elif uri[0] == 'parkings':
                if not any(d['ID'] == json_body['ID'] for d in catalog["parkings"]):
                    add_parking(catalog, json_body)
                    output = f"Parking with ID {json_body['ID']} has been added"
                else:
                    raise cherrypy.HTTPError(400, 'PARKING ALREADY REGISTERED')

            elif uri[0] == 'book':
                # Cerca il primo slot libero e prenotalo
                for device in catalog["devices"]:
                    if device.get('status') == 'free':
                        booking_code = str(uuid.uuid4())  # Genera un codice di prenotazione unico
                        device['status'] = 'occupied'  # Cambia lo stato in occupato
                        device['booking_code'] = booking_code  # Salva il codice di prenotazione nel dispositivo
                        json.dump(catalog, open(self.catalog_address, "w"), indent=4)
                        output = {
                            "message": f"Slot {device['location']} has been successfully booked.",
                            "booking_code": booking_code  # Restituisci il codice di prenotazione
                        }
                        break
                else:
                    output = {"message": "No free slots available at the moment."}

            else:
                raise cherrypy.HTTPError(404, 'Resource not found')

            return output

        except json.JSONDecodeError as e:
            cherrypy.log.error(f"JSON error: {str(e)}")
            raise cherrypy.HTTPError(500, 'JSON PARSE ERROR')

        except Exception as e:
            cherrypy.log.error(f"Error during POST request handling: {str(e)}")
            raise cherrypy.HTTPError(500, 'INTERNAL SERVER ERROR')



    def PUT(self, *uri, **params):
        try:
            catalog = json.load(open(self.catalog_address, "r"))
            body = cherrypy.request.body.read()
            json_body = json.loads(body.decode('utf-8'))
            if uri[0] == 'devices':
                for device in catalog["devices"]:
                    if device['ID'] == json_body['ID']:
                        device.update(json_body)  # Aggiorna tutti i campi inclusi 'status'
                        break
                else:
                    raise cherrypy.HTTPError(status=400, message='DEVICE NOT FOUND')
            elif uri[0] == 'services':
                update_service(catalog, json_body['ID'], json_body)
            elif uri[0] == 'users':
                update_user(catalog, json_body['ID'], json_body)
            elif uri[0] == 'parkings':
                update_parking(catalog, json_body['ID'], json_body)
            else:
                raise cherrypy.HTTPError(status=404, message='RESOURCE NOT FOUND')
            
            json.dump(catalog, open(self.catalog_address, "w"), indent=4)
            return json_body
        except json.JSONDecodeError as e:
            print(f"JSON error: {e}")  # Debug statement
            raise cherrypy.HTTPError(status=500, message='JSON PARSE ERROR')
        except Exception as e:
            print(f"Error during PUT request handling: {e}")  # Debug statement
            raise cherrypy.HTTPError(status=500, message='INTERNAL SERVER ERROR')
        
    def DELETE(self, *uri):
        try:
            catalog = json.load(open(self.catalog_address, "r"))
            if uri[0] == 'devices':
                removeDevices(catalog, uri[1])
                output = f"Device with ID {uri[1]} has been removed"
                print(output)
            elif uri[0] == 'services':
                remove_service(catalog, uri[1])
                output = f"Service with ID {uri[1]} has been removed"
            elif uri[0] == 'users':
                remove_user(catalog, uri[1])
                output = f"User with ID {uri[1]} has been removed"
            elif uri[0] == 'parkings':
                remove_parking(catalog, uri[1])
                output = f"Parking with ID {uri[1]} has been removed"
            else:
                raise cherrypy.HTTPError(status=404, message='RESOURCE NOT FOUND')
            
            json.dump(catalog, open(self.catalog_address, "w"), indent=4)
            return output
        except json.JSONDecodeError as e:
            print(f"JSON error: {e}")  # Debug statement
            raise cherrypy.HTTPError(status=500, message='JSON PARSE ERROR')
        except Exception as e:
            print(f"Error during DELETE request handling: {e}")  # Debug statement
            raise cherrypy.HTTPError(status=500, message='INTERNAL SERVER ERROR')

if __name__ == '__main__':
    catalogClient = CatalogREST("catalog.json")
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8080})
    cherrypy.tree.mount(catalogClient, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
    cherrypy.engine.exit()
