import logging
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import time
from threading import Timer, Lock
from pathlib import Path
import uuid
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Usa il backend non interattivo
import matplotlib.pyplot as plt
from dateutil import parser
from io import BytesIO

class IoTSmartParkingBot:
    def __init__(self, token, settings_path):
        self.token = token
        self.bot = telepot.Bot(self.token)
        self.settings = self.load_settings(settings_path)
        self.user_data = {}
        self.logged_in_users = {}
        self.lock = Lock()
        self.init_bot()

    def load_settings(self, path):
        with open(path, 'r') as file:
            return json.load(file)
    
    def init_bot(self):
        MessageLoop(self.bot, {
            'chat': self.handle_message,
            'callback_query': self.on_callback_query
        }).run_as_thread()
        print("Bot in esecuzione...")
    
    ### Gestione messaggi e callback
    
    def handle_message(self, msg):
        chat_id = msg['chat']['id']
        text = msg.get('text', '').strip().lower()
        
        if chat_id in self.logged_in_users and self.logged_in_users[chat_id]:
            if text == '/start':
                self.show_logged_in_menu(chat_id)
            else:
                self.bot.sendMessage(chat_id, "You are already logged in. Use the menu to choose an option.")
            return
        
        if chat_id in self.user_data and 'state' in self.user_data[chat_id]:
            self.process_state(chat_id, text)
            return
        
        if text == '/start':
            self.start(msg)
        elif text == '/parkings':
            self.reset_parking(chat_id)
        else:
            self.bot.sendMessage(chat_id, "Use /parkings to begin.")
    
    def on_callback_query(self, msg):

        query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')
        
        if query_data.startswith("select_parking_"):
            self.select_parking(chat_id, query_data)
        elif query_data == 'change_parking':
            self.handle_change_parking(chat_id)
        elif query_data == 'check':
            self.check_free_slots(chat_id)
        elif query_data == 'book':
            self.book_slot(chat_id)
        elif query_data == 'register':
            self.register(chat_id)
        elif query_data == 'login':
            self.login(chat_id)
        elif query_data == 'logout':
            self.logout(chat_id)
        elif query_data == 'wallet':
            self.show_wallet(chat_id)
        elif query_data == 'show_graphs':
            self.show_graphs(chat_id)
    
    ### Menu e navigazione
    
    def start(self, msg):
        chat_id = msg['chat']['id']
        if chat_id not in self.user_data or 'parking_name' not in self.user_data[chat_id]:
            self.bot.sendMessage(chat_id, "Hello! Choose a parking.")
            self.choose_parking(chat_id)
        else:
            self.bot.sendMessage(chat_id, f"Selected parking: {self.user_data[chat_id]['parking_name']}.")
            if chat_id in self.logged_in_users and self.logged_in_users[chat_id]:
                self.show_logged_in_menu(chat_id)
            else:
                self.show_initial_menu(chat_id)
    
    def show_initial_menu(self, chat_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Check free slots", callback_data='check')],
            [InlineKeyboardButton(text="📅 Book a slot", callback_data='book')],
            [InlineKeyboardButton(text="🚗 Parking (Change)", callback_data='change_parking')],
            [InlineKeyboardButton(text="🔑 Login", callback_data='login')],
            [InlineKeyboardButton(text="📝 Register to the system", callback_data='register')]
        ])
        self.bot.sendMessage(chat_id, 'Welcome to IoTSmartParking! Choose one of the following options:', reply_markup=keyboard)
    
    def show_logged_in_menu(self, chat_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Check free slots", callback_data='check')],
            [InlineKeyboardButton(text="📅 Book a slot", callback_data='book')],
            [InlineKeyboardButton(text="💳 Wallet", callback_data='wallet')],
            [InlineKeyboardButton(text="📊 Statistics visualization", callback_data='show_graphs')],
            [InlineKeyboardButton(text="🚗 Parking (Change)", callback_data='change_parking')],
            [InlineKeyboardButton(text="🔓 Logout", callback_data='logout')]
        ])
        self.bot.sendMessage(chat_id, "Choose an option:", reply_markup=keyboard)
    
    ### Registrazione
    
    def register(self, chat_id):
        self.bot.sendMessage(chat_id, "Type your name:")
        self.user_data[chat_id] = {'state': 'NAME'}
    
    def process_state(self, chat_id, text):
        state = self.user_data[chat_id]['state']
        
        if state == 'NAME':
            if self.is_valid_name(text):
                self.user_data[chat_id]['name'] = text
                self.bot.sendMessage(chat_id, "Type your surname:")
                self.user_data[chat_id]['state'] = 'SURNAME'
            else:
                self.bot.sendMessage(chat_id, "Name is not valid. Insert only letters.")
        
        elif state == 'SURNAME':
            if self.is_valid_name(text):
                self.user_data[chat_id]['surname'] = text
                self.bot.sendMessage(chat_id, "Type your identity card number (e.g., AAAA55555):")
                self.user_data[chat_id]['state'] = 'IDENTITY'
            else:
                self.bot.sendMessage(chat_id, "Surname is not valid. Insert only letters.")
        
        elif state == 'IDENTITY':
            if self.is_valid_identity(text):
                self.user_data[chat_id]['identity'] = text
                self.bot.sendMessage(chat_id, "Type your credit card number (16 digits):")
                self.user_data[chat_id]['state'] = 'CREDIT_CARD'
            else:
                self.bot.sendMessage(chat_id, "ID is not valid. Try again.")
        
        elif state == 'CREDIT_CARD':
            if self.is_valid_credit_card(text):
                self.user_data[chat_id]['credit_card'] = text
                user_id = self.send_user_data_to_catalog(chat_id)
                if user_id:
                    self.bot.sendMessage(chat_id, f"Registration complete! Your user ID is: {user_id}")
                    self.logged_in_users[chat_id] = True
                    self.show_initial_menu(chat_id)
                self.user_data[chat_id].pop('state', None)
            else:
                self.bot.sendMessage(chat_id, "Credit card is not valid. Try again.")
    
    ### Login
    
    def login(self, chat_id):
        self.bot.sendMessage(chat_id, "Type your name:")
        self.user_data[chat_id] = {'state': 'LOGIN_NAME'}
    
    def verify_login(self, chat_id):
        url = self.settings['catalog_url'] + '/users'
        headers = {'Content-Type': 'application/json'}
        login_name = self.user_data[chat_id].get('login_name', '').strip().lower()
        login_identity = self.user_data[chat_id].get('login_identity', '').strip().upper()
        
        try:
            response = requests.get(url, headers=headers)
            users = response.json().get("users", [])
            
            for user in users:
                if user['name'].lower() == login_name and user['identity'].upper() == login_identity:
                    self.logged_in_users[chat_id] = True
                    self.bot.sendMessage(chat_id, "Login successful!")
                    self.show_logged_in_menu(chat_id)
                    return
            
            self.bot.sendMessage(chat_id, "Credentials are not valid. Try again.")
            self.show_initial_menu(chat_id)
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Error during login: {e}")
            self.show_initial_menu(chat_id)


    def check_free_slots(self, msg):
        chat_id = msg['chat']['id']
        
        if chat_id not in self.user_data or 'parking_url' not in self.user_data[chat_id] or 'parking_port' not in self.user_data[chat_id]:
            bot.sendMessage(chat_id, "Plese select a parking before continue.")
            self.choose_parking(chat_id)
            return
        
        parking_url = self.user_data[chat_id]['parking_url']
        parking_port = self.user_data[chat_id]['parking_port']
        url = f'http://{parking_url}:{parking_port}/devices'

        try:
            response = requests.get(url)
            response.raise_for_status()
            slots = response.json()

            if isinstance(slots, str):
                slots = json.loads(slots)

            if not isinstance(slots, dict) or "devices" not in slots:
                raise ValueError("La risposta JSON non contiene un dizionario valido o manca la chiave 'devices'.")

            devices = slots.get("devices", [])
            if not isinstance(devices, list):
                raise ValueError("La risposta JSON non contiene una lista di dispositivi valida sotto la chiave 'devices'.")

            free_slots = [device["deviceInfo"] for device in devices if device.get("deviceInfo", {}).get("status") == "free"]
            
            if free_slots:
                slots_info = "\n".join([f"ID: {slot['location']}, Nome: {slot['name']}" for slot in free_slots])
                bot.sendMessage(chat_id, f'Avaiable slots:\n{slots_info}')
            else:
                bot.sendMessage(chat_id, 'There are no more avaiable parking slots now.')
        except Exception as e:
            bot.sendMessage(chat_id, f'Errore nel recupero dei dati dei posti: {e}')
    
    ### Prenotazione
    
    def book_slot(self, msg):
        chat_id = msg['chat']['id']
        book_url = 'http://127.0.0.1:8098/book'

        # Controllo se l'utente ha selezionato un parcheggio
        parking_url = self.user_data.get(chat_id, {}).get('parking_url')
        parking_port = self.user_data.get(chat_id, {}).get('parking_port')
        name_dev = self.user_data.get(chat_id, {}).get('parking_name', 'guest')  # Nome predefinito per utenti non registrati

        if not parking_url or not parking_port:
            bot.sendMessage(chat_id, "Error: Plese select a parking before book.")
            return

        url = f'http://{parking_url}:{parking_port}/get_best_parking'

        try:
            # Crea il payload per la richiesta
            if chat_id not in self.logged_in_users or not self.logged_in_users[chat_id]:
                data = {'booking_code': '', 'url': url, 'name': name_dev}
            else:
                data = {'booking_code': self.user_data[chat_id].get('book_code', ''), 'url': url, 'name': name_dev}

            headers = {'Content-Type': 'application/json'}
            book_response = requests.post(book_url, headers=headers, json=data)
            book_response.raise_for_status()

            r = book_response.json()
            slot_id = r.get('slot_id', 'N/A')
            location = r.get('location', 'N/A')
            name= r.get('name', 'N/A')
            print(f"Slot ID: {slot_id}, Location: {location}, Name: {name}")
            
            booking_code = r.get('booking_code', 'N/A')
            

            if chat_id in self.logged_in_users and self.logged_in_users[chat_id]:
                BC = self.user_data[chat_id].get('book_code', 'N/A')
                bot.sendMessage(chat_id, f"Your reserved slot is: {location}. Your booking code is: {BC}. \n Your parking slot will be reserved for 2 minutes.")
            else:
                bot.sendMessage(chat_id, f"Your reserved slot is: {location}. Your booking code is: {booking_code}. \n Your parking slot will be reserved for 2 minutes.")

            # Timer per la scadenza della prenotazione
            Timer(120, self.expire_reservation, args=[r, booking_code, msg]).start()

        except requests.exceptions.RequestException as e:
            bot.sendMessage(chat_id, f"Errore durante la comunicazione con il sistema di prenotazione: {e}")
        except Exception as e:
            bot.sendMessage(chat_id, f"Errore durante la prenotazione: {e}")
    
    ### Statistiche
    
    def show_stats(tot_dur,tot_fee,tot_park,chat_id):
        gas_price_per_litre =1.74
        diesel_fuel_per_litre =1.64
        avg_speed = 40
        co_2_gas = 108 # (g/km)
        co_2_diesel_fuel = 90
        diesel_fuel_avg_km_per_litre = 17
        gas_avg_km_per_litre = 13
        avg_ext_per_hour_park_fee = 1.5 #euros per hour 
        bot.sendMessage(chat_id, f"Calculating total stats... ")
        # STATS TO REACH OUR PARKINGS
        time_to_reach_parking_wc = 5 # min
        tot_time_to_reach_parking_wc =time_to_reach_parking_wc * tot_park
        tot_km_to_reach_parking_wc = tot_park * avg_speed/(60/time_to_reach_parking_wc)
        tot_money_to_reach_parking_diesel = (tot_km_to_reach_parking_wc/diesel_fuel_avg_km_per_litre) * diesel_fuel_per_litre
        tot_money_to_reach_parking_gas = (tot_km_to_reach_parking_wc/gas_avg_km_per_litre) * gas_price_per_litre
        co_2_to_reach_parking_diesel = tot_km_to_reach_parking_wc * co_2_diesel_fuel # (g)
        co_2_to_reach_parking_gas = tot_km_to_reach_parking_wc * co_2_gas #g
        # TODO: MAYBE PER WEEK,MONTH,YEAR?? add message
        print("Parking stats for diesel vehicles: \n")
        print(f"Total time to reach our parkings: {tot_time_to_reach_parking_wc} min")
        print(f"Total distance to reach our parkings: {tot_km_to_reach_parking_wc} km")
        print(f"Total money to reach our parkings: {tot_money_to_reach_parking_diesel} euros")
        print(f"Total CO2 emissions: {co_2_to_reach_parking_diesel} g")
        
        print("Parking stats for gas vehicles: \n")
        print(f"Total time to reach our parkings: {tot_time_to_reach_parking_wc} min")
        print(f"Total distance to reach our parkings: {tot_km_to_reach_parking_wc} km")
        print(f"Total money to reach our parkings: {tot_money_to_reach_parking_gas} euros")
        print(f"Total CO2 emissions: {co_2_to_reach_parking_gas} g")
        # bot.sendMessage(chat_id, f"Total stats while using our: {e}")
        
        #STATS NOT USING PARKINGS
        avg_time_to_park = 15
        tot_time_to_reach_ext_park =avg_time_to_park * tot_park
        tot_km_to_reach_ext_park = tot_park * avg_speed/(60/avg_time_to_park)
        tot_money_to_reach_ext_park_diesel = (tot_km_to_reach_ext_park/diesel_fuel_avg_km_per_litre) * diesel_fuel_per_litre
        tot_money_to_reach_ext_park_gas = (tot_km_to_reach_ext_park/gas_avg_km_per_litre) * gas_price_per_litre
        co_2_to_reach_ext_park_diesel = tot_km_to_reach_ext_park * co_2_diesel_fuel # (g)
        co_2_to_reach_ext_park_gas = tot_km_to_reach_ext_park * co_2_gas #g
        # TODO: MAYBE PER WEEK,MONTH,YEAR?? add message    
        
        print("Stats if our parkings were not used - diesel vehicles: \n")
        print(f"Total time to find outdoor parkings: {tot_time_to_reach_ext_park} min")
        print(f"Total distance to find outdoor parkings: {tot_km_to_reach_ext_park} km")
        print(f"Total money to find outdoor parkings: {tot_money_to_reach_ext_park_diesel} euros")
        print(f"Total c02 emission while searching outdoor parkings: {co_2_to_reach_ext_park_diesel} g")
        
        print("Stats if our parkings were not used - gas vehicles: \n")
        print(f"Total time to find outdoor parkings: {tot_time_to_reach_ext_park} min")
        print(f"Total distance to find outdoor parkings: {tot_km_to_reach_ext_park} km")
        print(f"Total money to find outdoor parkings: {tot_money_to_reach_ext_park_gas} euros")
        print(f"Total c02 emission while searching outdoor parkings: {co_2_to_reach_ext_park_gas} g")
        
        #TOTAL MONEY SPENT (INDOOR VS OUTDOOR, DIESEL VS GAS)
        
        tot_money_park_plus_reach_indoor_diesel  = tot_money_to_reach_parking_diesel + tot_fee
        tot_money_park_plus_reach_indoor_gas  =  tot_money_to_reach_parking_gas + tot_fee
        tot_money_park_plus_reach_outdoor_diesel = tot_money_to_reach_ext_park_diesel + tot_dur *  avg_ext_per_hour_park_fee
        tot_money_park_plus_reach_outdoor_gas = tot_money_to_reach_ext_park_gas + tot_dur * avg_ext_per_hour_park_fee
        # TODO: MAYBE PER WEEK,MONTH,YEAR?? add message
        print(f"Total money spent while using our services (money to reach parking plus fees) - diesel vehicles :{tot_money_park_plus_reach_indoor_diesel} euros\n")
        print(f"Total money spent while using our services (money to reach parking plus fees) - gas vehicles :{tot_money_park_plus_reach_indoor_gas} euros\n")
        print(f"Total money spent if our services were not used (money to find external parkings plus fees) - diesel vehicles :{tot_money_park_plus_reach_outdoor_diesel} euros\n")
        print(f"Total money spent if our services were not used (money to find external parkings plus fees) - gas vehicles :{tot_money_park_plus_reach_outdoor_gas} euros\n")
        
        #TOTAL CO2 EMISSIONS (INDOOR VS OUTDOOR, DIESEL VS GAS)
        
        tot_co2_indoor_gas = co_2_to_reach_parking_gas
        tot_co2_indoor_diesel = co_2_to_reach_parking_diesel
        tot_co2_outdoor_gas = co_2_to_reach_ext_park_diesel
        tot_co2_outdoor_diesel = co_2_to_reach_ext_park_diesel
        # TODO: MAYBE PER WEEK,MONTH,YEAR?? add message
        print(f"Total co2 emissions using our services - diesel vehicle: {tot_co2_indoor_diesel} g \n")
        print(f"Total co2 emissions using our services - gas vehicle: {tot_co2_indoor_gas} g\n")
        print(f"Total co2 emissions if our services were not used (co2 to find external parkings) - diesel vehicle: {tot_co2_outdoor_diesel} g\n")
        print(f"Total co2 emissions if our services were not used (co2 to find external parkings) - gas vehicle: {tot_co2_outdoor_gas} g\n")
        
        # SAVINGS
        saved_time = tot_time_to_reach_ext_park - tot_time_to_reach_ext_park
        saved_km = tot_km_to_reach_ext_park - tot_km_to_reach_parking_wc
        saved_co2_gas = tot_co2_outdoor_gas - tot_co2_indoor_gas
        saved_co2_diesel = tot_co2_outdoor_diesel - tot_co2_indoor_diesel
        saved_money_gas = tot_money_park_plus_reach_outdoor_gas - tot_money_park_plus_reach_indoor_gas
        saved_money_diesel = tot_money_park_plus_reach_outdoor_diesel - tot_money_park_plus_reach_indoor_diesel
        print("Savings achieved using our services:\n")
        print(f"Money saved - diesel vehicle: {saved_money_diesel} euros\n")
        print(f"Money saved - gas vehicle: {saved_money_gas} euros\n")
        print(f"Distance saved: {saved_km} km\n")
        print(f"co2 emissions saved - diesel vehicle: {saved_co2_diesel} g\n")
        print(f"co2 emissions saved - gas vehicle: {saved_co2_gas} g\n")
        print(f"Time saved: {saved_time} min\n")
        
        # TODO: MAYBE PER WEEK,MONTH,YEAR?? add message
    
    ### Wallet
    
    def show_wallet(self, msg):
        chat_id = msg['chat']['id']
        if chat_id not in self.logged_in_users or not self.logged_in_users[chat_id]:
            bot.sendMessage(chat_id, "Login is compulsory to see your wallet.")
            return

        url = 'http://127.0.0.1:5001/get_booking_info'
        headers = {'Content-Type': 'application/json'}
        data = {"booking_code": self.user_data[chat_id].get('book_code', '')}

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            response_data = response.json()
            if "transactions" in response_data and isinstance(response_data["transactions"], list):
                transactions = response_data["transactions"]
                message = "Your recent transactions:\n"
                for transaction in transactions:
                    slot_id = transaction.get("slot_id", "N/A")
                    duration = transaction.get("duration", "N/A")
                    fee = round(transaction.get("fee", 0), 2)
                    time = transaction.get("time", "N/A")
                    message += f"Slot: {slot_id}, Duration: {duration} hours, Fee: {fee} €, Date: {time}\n"
                bot.sendMessage(chat_id, message)
            else:
                bot.sendMessage(chat_id, "No transactions found.")

            # Mostra il menu principale
            self.show_logged_in_menu(chat_id)

        except Exception as e:
            bot.sendMessage(chat_id, f"Error retrieving transactions: {e}")


    def expire_reservation(self, selected_device, booking_code, msg):
        chat_id = msg['chat']['id']
        reservation_url = 'http://127.0.0.1:5001/reservation_exp'
        headers = {'Content-Type': 'application/json'}

        # Verifica che 'name_dev' esista in user_data
        name_dev = self.user_data.get(chat_id, {}).get('name_dev', 'guest')  # Default 'guest' se non registrato

        reservation_data = {
            "ID": selected_device['slot_id'],
            "name": selected_device.get('name', 'unknown'),
            "type": selected_device.get('type', 'unknown'),
            "location": selected_device.get('location', 'unknown'),
            "booking_code": booking_code,
            "name_dev": name_dev
        }

        try:
            req = requests.post(reservation_url, headers=headers, json=reservation_data)
            req.raise_for_status()

            response_data = req.json()
            print(f"Response JSON: {response_data}")

        except requests.exceptions.RequestException as e:
            print(f"Errore nella richiesta: {e}")
        except Exception as e:
            print(f"Errore generale: {e}")



if __name__ == "__main__":
    SETTINGS_PATH = Path(__file__).parent / "settings.json"
    TOKEN = '7501377611:AAGhXNYizRlkdl3V_BGtiIK-Slb76WcxzZ8'
    bot = IoTSmartParkingBot(TOKEN, SETTINGS_PATH)

    while True:
        time.sleep(10)