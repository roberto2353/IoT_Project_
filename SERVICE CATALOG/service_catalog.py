import cherrypy
import json
import time

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

class ServiceCatalogREST(object):
    exposed = True

    def __init__(self, catalog_address):
        self.catalog_address = catalog_address

    def GET(self, *uri, **params):
        catalog = json.load(open(self.catalog_address, "r"))
        if len(uri) == 0:
            raise cherrypy.HTTPError(status=400, message='UNABLE TO MANAGE THIS URL')
        elif uri[0] == 'all':
            output = catalog
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
        catalog = json.load(open(self.catalog_address, "r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        if uri[0] == 'services':
            if not any(d['ID'] == json_body['ID'] for d in catalog["services"]):
                add_service(catalog, json_body)
                output = f"Service with ID {json_body['ID']} has been added"
            else:
                raise cherrypy.HTTPError(status=400, message='SERVICE ALREADY REGISTERED')
        elif uri[0] == 'users':
            if not any(d['ID'] == json_body['ID'] for d in catalog["users"]):
                add_user(catalog, json_body)
                output = f"User with ID {json_body['ID']} has been added"
            else:
                raise cherrypy.HTTPError(status=400, message='USER ALREADY REGISTERED')
        elif uri[0] == 'parkings':
            if not any(d['ID'] == json_body['ID'] for d in catalog["parkings"]):
                add_parking(catalog, json_body)
                output = f"Parking with ID {json_body['ID']} has been added"
            else:
                raise cherrypy.HTTPError(status=400, message='PARKING ALREADY REGISTERED')
        else:
            raise cherrypy.HTTPError(status=404, message='RESOURCE NOT FOUND')

        json.dump(catalog, open(self.catalog_address, "w"), indent=4)
        return output

    def PUT(self, *uri, **params):
        catalog = json.load(open(self.catalog_address, "r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        if uri[0] == 'services':
            if not any(d['ID'] == json_body['ID'] for d in catalog["services"]):
                raise cherrypy.HTTPError(status=400, message='SERVICE NOT FOUND')
            else:
                update_service(catalog, json_body['ID'], json_body)
                output = f"Service with ID {json_body['ID']} has been updated"
        elif uri[0] == 'users':
            if not any(d['ID'] == json_body['ID'] for d in catalog["users"]):
                raise cherrypy.HTTPError(status=400, message='USER NOT FOUND')
            else:
                update_user(catalog, json_body['ID'], json_body)
                output = f"User with ID {json_body['ID']} has been updated"
        elif uri[0] == 'parkings':
            if not any(d['ID'] == json_body['ID'] for d in catalog["parkings"]):
                raise cherrypy.HTTPError(status=400, message='PARKING NOT FOUND')
            else:
                update_parking(catalog, json_body['ID'], json_body)
                output = f"Parking with ID {json_body['ID']} has been updated"
        else:
            raise cherrypy.HTTPError(status=404, message='RESOURCE NOT FOUND')

        json.dump(catalog, open(self.catalog_address, "w"), indent=4)
        return output

    def DELETE(self, *uri):
        catalog = json.load(open(self.catalog_address, "r"))
        if uri[0] == 'services':
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

if __name__ == '__main__':
    
    catalog_client = ServiceCatalogREST("service_catalog.json")
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.config.update({'server.socket_host': 'localhost', 'server.socket_port': 8084})
    cherrypy.tree.mount(catalog_client, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()

