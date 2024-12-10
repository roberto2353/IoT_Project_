
import json
from collections import defaultdict
from MyMQTT import MyMQTT
from pathlib import Path
from threading import Lock
import argparse
import os


P = Path(__file__).parent.absolute()
SETTINGS = P / 'settings.json'
path = Path(__file__).parent.parent.absolute()
P_DEV_1 = path / 'DEVICE_CONNECTOR' / 'settings.json'
class ParkModifier:
    def __init__(self):
        self.json_path = SETTINGS
        self.data = self.load_json()
        self.json_path_dev1 = P_DEV_1
        self.json_dev1 = self.load_dev1_json()

    def load_json(self):
        with open(self.json_path, 'r') as file:
            return json.load(file)
    def load_dev1_json(self):
        with open(self.json_path_dev1, 'r') as file:
            return json.load(file)

    def save_json(self):
        with open(self.json_path, 'w') as file:
            json.dump(self.data, file, indent=4)

    def get_last_id(self):
        if not self.data['devices']:
            return 0
        return max(device['deviceInfo']['ID'] for device in self.data['devices'])
    
    def get_last_id_dev1(self):
        if not self.json_dev1['devices']:
            return 0
        return max(device['deviceInfo']['ID'] for device in self.json_dev1['devices'])

    def add_floor(self):
        last_id = self.get_last_id()
        floors = {dev['deviceInfo']['location'].split('-')[0][1:] for dev in self.data['devices']}
        new_floor = max([int(floor) for floor in floors] + [-1]) + 1 
        for i in range(1, 8): 
            last_id += 1
            self.data['devices'].append({
                "deviceInfo": {
                    "ID": last_id,
                    "name": f"sensor{last_id}",
                    "type": "photocell",
                    "location": f"P{new_floor}-{i}",
                    "active": True
                }
            })
        self.save_json()
        self.data = self.load_json()

    def add_slot_to_floor(self, floor):
        last_id = self.get_last_id()
        slots = [dev['deviceInfo']['location'] for dev in self.data['devices'] if dev['deviceInfo']['location'].startswith(f"P{floor}-")]
        if not slots:
            raise ValueError(f"Il piano P{floor} non esiste.")
        new_slot = max(int(slot.split('-')[1]) for slot in slots) + 1
        last_id += 1
        self.data['devices'].append({
            "deviceInfo": {
                "ID": last_id,
                "name": f"sensor{last_id}",
                "type": "photocell",
                "location": f"P{floor}-{new_slot}",
                "active": True
            }
        })
        self.save_json()
        self.data = self.load_json()

    def remove_floor(self, floor):
        self.data['devices'] = [dev for dev in self.data['devices'] if not dev['deviceInfo']['location'].startswith(f"P{floor}-")]
        self.save_json()
        self.data = self.load_json()

    def remove_slot(self, floor, slot):
        location = f"P{floor}-{slot}"
        self.data['devices'] = [dev for dev in self.data['devices'] if dev['deviceInfo']['location'] != location]
        self.save_json()
        self.data = self.load_json()
    
    def adjust_devices(self):
        
        """Aggiorna gli ID e i nomi dei dispositivi per evitare interferenze."""
        current_id = self.get_last_id_dev1()
        for device in self.data['devices']:
            current_id += 1
            device['deviceInfo']['ID'] = current_id
            device['deviceInfo']['name'] = f"sensor{current_id}"
        self.save_json()  
        
def main():
    parser = argparse.ArgumentParser(description="Modify parking devices.")
    parser.add_argument("action", type=str, choices=["add_floor", "add_slot", "remove_floor", "remove_slot"], 
                        help="Action to exec: add_floor, add_slot, remove_floor, remove_slot")
    parser.add_argument("--floor", type=int, help="Specify floor.")
    parser.add_argument("--slot", type=int, help="Specify slot.")

    args = parser.parse_args()

    # Inizializza il ParkingManager
    manager = ParkModifier()

    if args.action == "add_floor":
        manager.adjust_devices()
        manager.add_floor()
        print("New floor added successfully with 7 slots")

    elif args.action == "add_slot":
        if args.floor is None:
            print("Error: to add a slot please specify a floor with --floor")
            return
        manager.adjust_devices()
        manager.add_slot_to_floor(args.floor)
        print(f"New slot added at floor {args.floor}.")
    elif args.action == "remove_floor":
        if args.floor is None:
            print("Error: to remove a floor specify it with --floor.")
            return
        manager.adjust_devices()
        manager.remove_floor(args.floor)
        print(f"Floor {args.floor} removed.")

    elif args.action == "remove_slot":
        if args.floor is None or args.slot is None:
            print("Error: to remove a slot specify the floor (--floor) and the slot (--slot).")
            return
        manager.adjust_devices()
        manager.remove_slot(args.floor, args.slot)
        print(f"Slot {args.slot} on floor {args.floor} removed.")

if __name__ == "__main__":
    main()