### sensor.py

Contains the class SensorREST which:
- contains the simulation, directly calling the entranceAlgorithmService class (see below)
- is subscribed to all devices status topic
- via pingCatalog() sends messages for all sensors with the current time to the catalog.
- via  start_periodic_updates() starts a background thread that publishes periodic updates via MQTT read by the catalog
- via register_parking() sends to the catalog the information to register its parking, taking them from the setting.json in the dictionary corresponding to key "parkingInfo"

- REST'S GET method can be used to return the devices or find the best free parking to reserve (see below)
- REST'S POST method allows to switch state from active= "True" to "False", triggering also the change of setting_status.json and class devices

- myOnMessageReceived(...) allows to update some field of the devices and store them into the setting_status.json



### entranceAlgorithm.py

This file contains the class Algorithm entitled to do a simulation both on arrivals(of non-users of our system) and departures(non-users and registered users).
The simulation is all based on a loop that is anticipated by a deletion and reinitialization of a JSON file which contains the main informations of the sensor for the parking.This file is called setting_status.json and is based on the setting.json file (which is "static", doesn't get updated at runtime).
In the loop, repeated every 60 seconds, there are first methods used to update the variables of the class like the devices themselves, the number of floors, devices, occupied devices and occupied devices per floor. After them we handle first the departures, with some conditions to make our simulation more realistic like:
- only cars that have been in the parking for at least 30 min (6-24) or 1  hour (0-6) can leave it.
- eligible cars will depart with a probability of 10%, meaning that since this loop is repeated every 60 sec, each min we ave a probability of 10% that an eligible car leaves the parking (tries to push cars to stay more than the threshold so that we have more realistic values)
- cars leaving cause a POST to the exit, which calculates the fee and the durations and return them to the algorithm. These info are used to both update the setting_status.json, both to publish a message with the event of the update of the device to the adaptor, which will write the updated device on 2 dbs, one for the current state of devices, one for the duration and fee tracking.
After the departures, class variables are updated again and then the arrival_time function is called:
this function is used to schedule the next arrival, which is saved into a class list of "times" sorted so that he first element is the closest temporally. Arrivals are scheduled every 7,5-15 min (0-6) or 2-7 min (6-24) and only if the parking is not full, leaving at least one slot free (for the simplicity of our reservation tries).
Finally, arrivals are routed in routeArrivals():
-just if the current time is greater compared to first element of the list of arrivals
-following a balancing algorithm: first cars occupy the first floor until 80% of it is full, then they move to the upper floor and so on... until all floors are 80% occupied. When this happens, they start to occupy again slots at the first floor.
-there is also the possibility of using a flag when calling this method. this is used in the reservation procedure to find the best slot to reserve directly via Telegram bot.

This whole class is called by class EntranceAlgorithmService, which simply runs the loop as a thread and exposes a method to find the best park with the flag for the reservation  of a slot.





### parkingModifier.py

Simple script which allows to modify directly the setting,json file, so that floors and slots can be added or removed before running any container. the ID  of a slot in the case of a deletion doesn't get modified (leaving some "holes") so that we ensure meaningful stats and values on the DBs (the ID once created is always the same)
in the case of parkings except the first (Device_connector 1), ids will start from the last of the previous parking in order to avoid conflicts in POST of update of sensors state



 