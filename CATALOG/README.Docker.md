### CATALOG
It works both as a service and a device catalog.
In particular, it provides both REST and MQTT communication protocols to add/retrieve/update/delete new devices, services, users and parkings.

### Contents
The REST API allows to retrieve data, and the POST method is used to register devices, services, users and parkings for the first time, while an MQTT subscriber is used to update the timestamp of devices and services: if the timestamp is not updated for a SERVICE_EXPIRATION_THRESHOLD = 120 seconds and DEVICE_EXPIRATION_THRESHOLD =  180 seconds, the corresponding devices/services are assumed to be not reachable and they are removed from the catalog.
More details on this in next sections.

### REST API

### MQTT

### Building and running your application
In order to launch this application as a Docker container, you first need to make sure to have Docker installed, then build your image e.g.: `docker build -t catalog .`.
Then run it with this command: `docker run -d --name catalog --network IoT_Parking -p 8090:8090 -v catalog:/app/catalog catalog`
Your application will be available at http://catalog:8090.
You can change the port on which the catalog web service is run by changing the "port" field in "catalog" dictionary inside "catalog.json".
Consult Docker's [getting started](https://docs.docker.com/)
docs for more detail on building and running.

### References
* [Docker's Python guide](https://docs.docker.com/language/python/)