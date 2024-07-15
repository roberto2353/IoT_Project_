import json
import paho.mqtt.client as mqtt
import requests
import threading
import time
import signal
import sys

RESOURCE_CATALOG_URL = 'http://localhost:8080/catalog/devicesList'
BROKER_URL = 'test.mosquitto.org'
BROKER_PORT = 1883
UPDATE_INTERVAL = 60  

running = True

def get_devices():
    response = requests.get(RESOURCE_CATALOG_URL)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching devices: {response.status_code}")
        return []

def register_device(device):
    response = requests.post(RESOURCE_CATALOG_URL, json=device)
    if response.status_code == 201:
        print(f"Device {device['name']} registered successfully.")
    else:
        print(f"Error registering device {device['name']}: {response.status_code}")

def update_device(device):
    device_id = device.get('id')
    if device_id is not None:
        response = requests.put(f"{RESOURCE_CATALOG_URL}/{device_id}", json=device)
        if response.status_code == 200:
            print(f"Device {device['name']} updated successfully.")
        else:
            print(f"Error updating device {device['name']}: {response.status_code}")


def remove_device(device_id):
    response = requests.delete(f"{RESOURCE_CATALOG_URL}/{device_id}")
    if response.status_code == 204:
        print(f"Device {device_id} removed successfully.")
    else:
        print(f"Error removing device {device_id}: {response.status_code}")


def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    devices = get_devices()
    for device in devices:
        topic = device['topic']
        client.subscribe(topic)
        print(f"Subscribed to topic: {topic}")


def on_message(client, userdata, msg):
    print(f"Message received on topic {msg.topic}: {msg.payload.decode()}")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

def continuous_update():
    while running:
        devices = get_devices()
        for device in devices:
            update_device(device)
        time.sleep(UPDATE_INTERVAL)


def signal_handler(sig, frame):
    global running
    print("Graceful shutdown initiated.")
    running = False
    devices = get_devices()
    for device in devices:
        remove_device(device['id'])
    client.loop_stop()
    client.disconnect()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


client.connect(BROKER_URL, BROKER_PORT, 60)
client.loop_start()


update_thread = threading.Thread(target=continuous_update)
update_thread.start()


try:
    while running:
        pass
except KeyboardInterrupt:
    print("Exiting...")
    signal_handler(signal.SIGINT, None)
