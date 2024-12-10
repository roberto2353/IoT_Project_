### ***CATALOG***
It works both as a service and a device catalog.
In particular, it provides both REST and MQTT communication protocols to add/retrieve/update/delete new devices, services, users and parkings.

### ***Contents***

- ***"settings.json"*** contains the info needed for the MQTT connection
- ***"catalog.json"*** contains the info about IP address and port of catalog service, and then contains four lists:
1. "devices", which contains all the active devices in the system;
2. "services", which contains all the active services in the system;
3. "users", which contains all the users in the system, both the telegram users and administrator profiles which have administrator privilidges to run the ***"parking_stats.py"*** and ***"WebService.py"*** web pages in ***DATA*** container;
4. "parkings", which contains all parkings in the system;
The GET method allows to retrieve data, and the POST method is used to register devices, services, users and parkings for the first time, while an MQTT subscriber is used to update the timestamp of devices and services: if the timestamp is not updated for a ***SERVICE_EXPIRATION_THRESHOLD*** = 120 seconds and ***DEVICE_EXPIRATION_THRESHOLD*** =  180 seconds, the corresponding devices/services are assumed to be not reachable and they are removed from the catalog.
More details on this in next sections.

### ***REST API***
The catalog service exposes ***POST***, ***GET***, ***PUT*** and ***DELETE*** methods.
- ***GET***
1. /all
2. /devices
3. /services
4. /users
5. /parkings

- ***POST***
1. /devices
2. /services
3. /users
4. /parkings

- ***PUT***
1. /devices
2. /services
3. /users
4. /parkings

- ***DELETE***
1. /devices
2. /services
3. /users
4. /parkings

All those methods call the "catalog_manager" class, which handles correctly the retrieval, insertion, deletion, update inside "catalog.json" file, keeping it updated.
Moreover, when a new device is registered through POST method, the catalog sends the data about the device to the adaptor, in order to store it in the database.
### ***MQTT***

The catalog has also an MQTT subscriber to topic ***"ParkingLot/alive/+"***, where the "+" indicates that the last field can be anything. In fact, it receives alive messages both from devices and services, that are distinguished from the "bn" field in the SenML format:

- message = {
                        "bn": "updateCatalogService",  
                        "e": [
                            {
                                "n": f"{self.serviceID}",  
                                "u": "IP",  
                                "t": str(time.time()), 
                                "v": ""  
                            }
                        ]
            }

- message = {
                        "bn": "updateCatalogSlot",  
                        "e": [
                            {
                                "n": f"{device['ID']}",  
                                "u": "IP",  
                                "t": str(time.time()), 
                                "v": ""  
                            }
                        ]
            }

Each time it receives a message, it updates the timestamp of that device/service in the "catalog.json", so that they are always up to date.
### ***Building and running your application***
In order to launch this application as a Docker container, you need to follow these steps:
-make sure to have Docker installed
-you can change the port on which the catalog web service is run by changing the ***"port"*** field in ***"catalog"*** dictionary inside ***"catalog.json"***.
-build your image e.g.: `docker build -t catalog .`.
-run it with this command: `docker run -d --name catalog --network IoT_Parking -p 8090:8090 -v catalog:/app/catalog catalog`
Your application will be available at http://catalog:8090.
You can change the port on which the catalog web service is run by changing the "port" field in "catalog" dictionary inside "catalog.json".
Consult Docker's [getting started](https://docs.docker.com/)
docs for more detail on building and running.

### References
* [Docker's Python guide](https://docs.docker.com/language/python/)