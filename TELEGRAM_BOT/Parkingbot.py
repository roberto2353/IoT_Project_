import logging
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import time
import random
import string
from threading import Timer
from threading import Lock
from pathlib import Path
import uuid
import numpy as np
from datetime import datetime
import matplotlib

matplotlib.use('Agg')  # Usa il backend non interattivo
import matplotlib.pyplot as plt
from dateutil import parser
from io import BytesIO
import requests
from dateutil import parser


def loadSettings():
    # Percorso al file delle impostazioni
    P = Path(__file__).parent.absolute()
    SETTINGS_PATH = P / 'settings.json'
    with Lock():
        # Carica le impostazioni
        with open(SETTINGS_PATH, 'r') as file:
            settings = json.load(file)
            return settings


def format_datetime(datetime_str):
    """Converte una stringa datetime ISO in un formato leggibile."""
    try:
        dt = parser.parse(datetime_str)
        return dt.strftime("On: %d-%m-%Y  %H:%M:%S")
    except Exception as e:
        return "Invalid date and time"


def format_duration(duration):
    """Converte una durata in ore in un formato leggibile."""
    if duration == "N/A" or duration is None:
        return "N/A"

    try:
        total_seconds = duration * 3600  # Converti ore in secondi
        if total_seconds >= 3600:  # Se è più di un'ora
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            return f"{hours} hours and {minutes} minutes"
        elif total_seconds >= 60:  # Se è più di un minuto
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            return f"{minutes} minutes and {seconds} seconds"
        else:  # Altrimenti in secondi
            return f"{int(total_seconds)} seconds"
    except Exception as e:
        return "Invalid duration"


def is_valid_name(name):
    return name.isalpha()


def is_valid_identity(id_number):
    return id_number.isalnum() and len(id_number) == 9


def is_valid_credit_card(card_number):
    return card_number.isdigit() and len(card_number) == 16


class ParkingBot:
    def __init__(self):
        self.query_data = None
        self.chat_id = None
        self.query_id = None
        self.settings = loadSettings
        # Token del bot Telegram
        self.TOKEN = '7501377611:AAGhXNYizRlkdl3V_BGtiIK-Slb76WcxzZ8'

        # Stati per la registrazione
        self.NAME, self.SURNAME, self.IDENTITY, self.CREDIT_CARD = range(4)

        # Dati utente e stati di login
        self.user_data = {}
        self.logged_in_users = {}

    # Funzione per validare il nome

    def show_logged_in_menu(self):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Check free slots", callback_data='check')],
            [InlineKeyboardButton(text="📅 Book a slot", callback_data='book')],
            [InlineKeyboardButton(text="💳 Wallet", callback_data='wallet')],
            [InlineKeyboardButton(text="📊 Statistics visualization", callback_data='show_graphs')],
            [InlineKeyboardButton(text="🚗 Parking (Change)", callback_data='change_parking')],
            [InlineKeyboardButton(text="🔓 Logout", callback_data='logout')]
        ])
        bot.sendMessage(self.chat_id, "Choose one option:", reply_markup=keyboard)

    def show_initial_menu(self):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Check free slots", callback_data='check')],
            [InlineKeyboardButton(text="📅 Book a slot", callback_data='book')],
            [InlineKeyboardButton(text="🚗 Parking (Change)", callback_data='change_parking')],
            [InlineKeyboardButton(text="🔑 Login", callback_data='login')],
            [InlineKeyboardButton(text="📝 Register to the system", callback_data='register')]
        ])
        bot.sendMessage(self.chat_id, 'Welcome to the IoTSmartParking! Choose one of the following options:',
                        reply_markup=keyboard)

    def choose_parking(self):
        catalog_url = self.settings['catalog_url'] + '/parkings'
        response = requests.get(catalog_url)
        print("Risposta del catalogo per /parkings:", response.text)  # Log del risultato

        try:
            parkings = response.json().get("parkings", [])
            if not parkings:
                bot.sendMessage(self.chat_id, "There are no more free parking slots now.")
                return

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=parking["name"], callback_data=f"select_parking_{parking['ID']}")]
                for parking in parkings
            ])

            bot.sendMessage(self.chat_id, "Choose a parking:", reply_markup=keyboard)
        except Exception as e:
            bot.sendMessage(self.chat_id, f"Errore nel recupero dei parcheggi: {e}")

    def handle_change_parking(self, chat_id):
        bot.sendMessage(chat_id, "Select a parking from the list:")
        self.choose_parking()

    def start(self, msg):
        self.chat_id = msg['chat']['id']
        if self.chat_id not in self.user_data or 'parking_name' not in self.user_data[self.chat_id]:
            bot.sendMessage(self.chat_id,
                            "Hello! Choose the parking you prefer. \nIf you need to change the parking, do it writing /parkings or from the menu button.")
            self.choose_parking()
        else:
            bot.sendMessage(self.chat_id, f"Selected parking: {self.user_data[self.chat_id]['parking_name']}.")
            if self.chat_id in self.logged_in_users and self.logged_in_users[self.chat_id]:
                self.show_logged_in_menu()
            else:
                self.show_initial_menu()

    def reset_parking(self, msg):
        self.chat_id = msg['chat']['id']
        if self.chat_id in self.user_data:
            self.user_data[self.chat_id].pop('parking_name', None)
            self.user_data[self.chat_id].pop('parking_url', None)
            self.user_data[self.chat_id].pop('parking_port', None)
        bot.sendMessage(self.chat_id, "Select a again the parking:")
        self.choose_parking()

    def on_callback_query(self, msg):
        self.query_id, self.chat_id, self.query_data = telepot.glance(msg, flavor='callback_query')

        if self.query_data.startswith("select_parking_"):
            parking_id = int(self.query_data.split("_")[-1])

            catalog_url = self.settings['catalog_url'] + '/parkings'
            response = requests.get(catalog_url)
            parkings = response.json().get("parkings", [])

            for parking in parkings:
                if parking["ID"] == parking_id:
                    if self.chat_id not in self.user_data:
                        self.user_data[self.chat_id] = {}
                    self.user_data[self.chat_id].update({
                        "parking_url": parking["url"],
                        "parking_port": parking["port"],
                        "parking_name": parking["name"]
                    })

                    bot.sendMessage(self.chat_id, f"Parking {parking['name']} selected!")

                    # Mostra il menu aggiornato
                    if self.chat_id in self.logged_in_users and self.logged_in_users[self.chat_id]:
                        self.show_logged_in_menu()
                    else:
                        self.show_initial_menu()
                    break

        elif self.query_data == 'change_parking':
            self.handle_change_parking(self.chat_id)

        elif self.query_data == 'check':
            self.check_free_slots({'chat': {'id': self.chat_id}})
            self.show_logged_in_menu() if self.chat_id in self.logged_in_users and self.logged_in_users[
                self.chat_id] else self.show_initial_menu()

        elif self.query_data == 'book':
            self.book_slot({'chat': {'id': self.chat_id}})
            self.show_logged_in_menu() if self.chat_id in self.logged_in_users and self.logged_in_users[
                self.chat_id] else self.show_initial_menu()

        elif self.query_data == 'register':
            self.register({'chat': {'id': self.chat_id}})

        elif self.query_data == 'login':
            self.login({'chat': {'id': self.chat_id}})

        elif self.query_data == 'logout':
            self.logout()

        elif self.query_data == 'wallet':
            self.show_wallet({'chat': {'id': self.chat_id}})
            self.show_logged_in_menu() if self.chat_id in self.logged_in_users and self.logged_in_users[
                self.chat_id] else self.show_initial_menu()

        elif self.query_data == 'show_graphs':
            self.show_graphs({'chat': {'id': self.chat_id}})

    def register(self, msg):
        self.chat_id = msg['chat']['id']
        bot.sendMessage(self.chat_id, "Type your name:")
        self.user_data[self.chat_id] = {'state': self.NAME}

    def login(self, msg):
        self.chat_id = msg['chat']['id']
        # Verifica se il parcheggio è stato selezionato DECIDIDIAMO SE SIA NECESSARIO???????
        # if chat_id not in user_data or 'parking_name' not in user_data[chat_id]:
        #    bot.sendMessage(chat_id, "Prima di fare il login, seleziona un parcheggio.")
        #    choose_parking()
        #    return

        # Se il parcheggio è selezionato, avvia il processo di login
        bot.sendMessage(self.chat_id, "Type your name for the login process:")
        self.user_data[self.chat_id]['state'] = 'LOGIN_NAME'

    def handle_message(self, msg):
        self.chat_id = msg['chat']['id']
        text = msg.get('text', '').strip().lower()

        # Se l'utente è loggato
        if self.chat_id in self.logged_in_users and self.logged_in_users[self.chat_id]:
            if text == '/start':
                self.show_logged_in_menu()
            else:
                bot.sendMessage(self.chat_id, "You are already logged in. Use the menu to choose an option.")
            return

        # Se l'utente è nel processo di login
        if self.chat_id in self.user_data and 'state' in self.user_data[self.chat_id]:
            self.process_state(text)
            return

        # Se l'utente non è loggato né in login, avvia il menu iniziale
        if text == '/start':
            self.start(msg)
        elif text == '/parkings':
            self.reset_parking(msg)
        else:
            bot.sendMessage(self.chat_id, "Use /parkings to begin.")

    def process_state(self, text):
        state = self.user_data[self.chat_id]['state']

        if state == self.NAME:
            if is_valid_name(text):
                self.user_data[self.chat_id]['name'] = text
                bot.sendMessage(self.chat_id, "Type your surname:")
                self.user_data[self.chat_id]['state'] = self.SURNAME
            else:
                bot.sendMessage(self.chat_id, "Name is not valid, insert only letters.")

        elif state == self.SURNAME:
            if is_valid_name(text):
                self.user_data[self.chat_id]['surname'] = text
                bot.sendMessage(self.chat_id, "Type our identity card number (es. AAAA55555):")
                self.user_data[self.chat_id]['state'] = self.IDENTITY
            else:
                bot.sendMessage(self.chat_id, "Surname is not valid, insert only letters.")

        elif state == self.IDENTITY:
            if is_valid_identity(text):
                self.user_data[self.chat_id]['identity'] = text
                bot.sendMessage(self.chat_id, "Type your credit card number (16 numbers):")
                self.user_data[self.chat_id]['state'] = self.CREDIT_CARD
            else:
                bot.sendMessage(self.chat_id, "ID number is not valid. Insert it again.")

        elif state == self.CREDIT_CARD:
            if is_valid_credit_card(text):
                self.user_data[self.chat_id]['credit_card'] = text
                id = self.send_user_data_to_catalog(self.user_data, self.chat_id)
                if id:
                    bot.sendMessage(self.chat_id,
                                    f"Registration process complete!\nUse your card or the associated number: {id} for login in the system and access your wallet ,statistics and book a slot.")
                    del self.user_data[self.chat_id]['state']
                    self.show_initial_menu()
                if 'state' in self.user_data[self.chat_id]:
                    del self.user_data[self.chat_id]['state']
            else:
                bot.sendMessage(self.chat_id, "Credit card number is not valid. Insert it again.")

        elif state == 'LOGIN_NAME':
            if is_valid_name(text):
                self.user_data[self.chat_id]['login_name'] = text
                bot.sendMessage(self.chat_id, "Type our identity card number:")
                self.user_data[self.chat_id]['state'] = 'LOGIN_IDENTITY'
            else:
                bot.sendMessage(self.chat_id, "Nome not found. Type your name again.")

        elif state == 'LOGIN_IDENTITY':
            if is_valid_identity(text):
                self.user_data[self.chat_id]['login_identity'] = text
                self.verify_login()
            else:
                bot.sendMessage(self.chat_id, "ID card not found or associated to another person. Type it again")

        else:
            bot.sendMessage(self.chat_id,
                            "Welcome back to IoT_SmartParking bot!\nYou could check avaiable spots and book it here.\nType /start")

    def verify_login(self):
        url = f"{self.settings['catalog_url']}/users"
        headers = {'Content-Type': 'application/json'}

        login_name = self.user_data[self.chat_id].get('login_name', '').strip().lower()
        login_identity = self.user_data[self.chat_id].get('login_identity', '').strip().upper()

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            users = response.json().get("users", [])

            for user in users:
                catalog_name = user['name'].strip().lower()
                catalog_identity = user['identity'].strip().upper()

                if catalog_name == login_name and catalog_identity == login_identity:
                    self.logged_in_users[self.chat_id] = True
                    self.user_data[self.chat_id]["book_code"] = user['ID']
                    bot.sendMessage(self.chat_id, "Login successful!")
                    self.show_logged_in_menu()
                    return

                    # Credenziali non valide
            bot.sendMessage(self.chat_id, "Credentials are not valid. Try again.")
            self.show_initial_menu()

        except requests.exceptions.RequestException as e:
            bot.sendMessage(self.chat_id, f"Error during the login process: {e}")
            self.show_initial_menu()

    def show_wallet(self, msg):
        self.chat_id = msg['chat']['id']
        if self.chat_id not in self.logged_in_users or not self.logged_in_users[self.chat_id]:
            bot.sendMessage(self.chat_id, "Login is compulsory to see your wallet.")
            return

        url = 'http://127.0.0.1:5001/get_booking_info'
        headers = {'Content-Type': 'application/json'}
        data = {"booking_code": self.user_data[self.chat_id].get('book_code', '')}

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            response_data = response.json()
            if "transactions" in response_data and isinstance(response_data["transactions"], list):
                transactions = response_data["transactions"]
                message = "Your recent transactions:\n"
                for transaction in transactions:
                    slot_id = transaction.get("slot_id", "N/A")
                    raw_duration = transaction.get("duration", "N/A")
                    formatted_duration = format_duration(raw_duration)
                    fee = round(transaction.get("fee", 0), 2)
                    raw_time = transaction.get("time", "N/A")
                    formatted_time = format_datetime(raw_time)
                    message += f"Slot: {slot_id}, Duration: {formatted_duration}, Fee: {fee} €,\n{formatted_time}\n"
                bot.sendMessage(self.chat_id, message)
            else:
                bot.sendMessage(self.chat_id, "No transactions found.")

        except Exception as e:
            bot.sendMessage(self.chat_id, f"Error retrieving transactions: {e}")

    def send_user_data_to_catalog(self, user_data, chat_id):
        url = self.settings['catalog_url'] + '/users'
        headers = {'Content-Type': 'application/json'}
        id = str(uuid.uuid4())

        user_info = {
            "ID": id,
            "name": user_data['name'],
            "surname": user_data['surname'],
            "identity": user_data['identity'],
            "credit_card": user_data['credit_card']
        }

        try:
            response = requests.post(url, headers=headers, json=user_info)
            response.raise_for_status()
            return id

        except requests.exceptions.HTTPError as http_err:
            bot.sendMessage(chat_id, f"Errore HTTP: {http_err}")
        except Exception as err:
            bot.sendMessage(chat_id, f"Errore: {err}")

        return None

    def logout(self):
        if self.chat_id in self.logged_in_users:
            del self.logged_in_users[self.chat_id]
            bot.sendMessage(self.chat_id, "Logout successful.")
        else:
            bot.sendMessage(self.chat_id, "You are not logged in the system.")

        self.show_initial_menu()

    def check_free_slots(self, msg):
        self.chat_id = msg['chat']['id']

        if (self.chat_id not in self.user_data or 'parking_url' not in
                self.user_data[self.chat_id] or 'parking_port' not in self.user_data[self.chat_id]):
            bot.sendMessage(self.chat_id, "Plese select a parking before continue.")
            self.choose_parking()
            return

        parking_url = self.user_data[self.chat_id]['parking_url']
        parking_port = self.user_data[self.chat_id]['parking_port']
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
                raise ValueError(
                    "La risposta JSON non contiene una lista di dispositivi valida sotto la chiave 'devices'.")

            free_slots = [device["deviceInfo"] for device in devices if
                          device.get("deviceInfo", {}).get("status") == "free"]

            if free_slots:
                slots_info = "\n".join([f"ID: {slot['location']}, Nome: {slot['name']}" for slot in free_slots])
                bot.sendMessage(self.chat_id, f'Avaiable slots:\n{slots_info}')
            else:
                bot.sendMessage(self.chat_id, 'There are no more avaiable parking slots now.')
        except Exception as e:
            bot.sendMessage(self.chat_id, f'Errore nel recupero dei dati dei posti: {e}')

    def book_slot(self, msg):
        self.chat_id = msg['chat']['id']
        book_url = 'http://127.0.0.1:8098/book'

        # Controllo se l'utente ha selezionato un parcheggio
        parking_url = self.user_data.get(self.chat_id, {}).get('parking_url')
        parking_port = self.user_data.get(self.chat_id, {}).get('parking_port')
        name_dev = self.user_data.get(self.chat_id, {}).get('parking_name',
                                                            'guest')  # Nome predefinito per utenti non registrati

        if not parking_url or not parking_port:
            bot.sendMessage(self.chat_id, "Error: Plese select a parking before book.")
            return

        url = f'http://{parking_url}:{parking_port}/get_best_parking'

        try:
            # Crea il payload per la richiesta
            if self.chat_id not in self.logged_in_users or not self.logged_in_users[self.chat_id]:
                data = {'booking_code': '', 'url': url, 'name': name_dev}
            else:
                data = {'booking_code': self.user_data[self.chat_id].get('book_code', ''), 'url': url, 'name': name_dev}

            headers = {'Content-Type': 'application/json'}
            book_response = requests.post(book_url, headers=headers, json=data)
            book_response.raise_for_status()

            r = book_response.json()
            slot_id = r.get('slot_id', 'N/A')
            location = r.get('location', 'N/A')
            name = r.get('name', 'N/A')
            print(f"Slot ID: {slot_id}, Location: {location}, Name: {name}")

            booking_code = r.get('booking_code', 'N/A')

            if self.chat_id in self.logged_in_users and self.logged_in_users[self.chat_id]:
                BC = self.user_data[self.chat_id].get('book_code', 'N/A')
                bot.sendMessage(self.chat_id,
                                f"Your reserved slot is: {location}. Your booking code is: {BC}. \n Your parking slot will be reserved for 2 minutes.")
            else:
                bot.sendMessage(self.chat_id,
                                f"Your reserved slot is: {location}. Your booking code is: {booking_code}. \n Your parking slot will be reserved for 2 minutes.")

            # Timer per la scadenza della prenotazione
            Timer(120, self.expire_reservation, args=[r, booking_code, msg]).start()

        except requests.exceptions.RequestException as e:
            bot.sendMessage(self.chat_id, f"Errore durante la comunicazione con il sistema di prenotazione: {e}")
        except Exception as e:
            bot.sendMessage(self.chat_id, f"Errore durante la prenotazione: {e}")

    def expire_reservation(self, selected_device, booking_code, msg):
        self.chat_id = msg['chat']['id']
        reservation_url = 'http://127.0.0.1:5001/reservation_exp'
        headers = {'Content-Type': 'application/json'}

        # Verifica che 'name_dev' esista in user_data
        name_dev = self.user_data.get(self.chat_id, {}).get('name_dev', 'guest')  # Default 'guest' se non registrato

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

    def show_graphs(self, msg):
        self.chat_id = msg['chat']['id']
        if self.chat_id not in self.logged_in_users or not self.logged_in_users[self.chat_id]:
            bot.sendMessage(self.chat_id, "Login is compulsory to see your statistics.")
            return

        try:
            # URL di base per il servizio REST
            base_url = 'http://127.0.0.1:5001'

            # Ottieni ID utente
            user_id = self.user_data[self.chat_id].get('book_code', '')
            print("ID utente:", user_id)
            parking_id = self.user_data[self.chat_id].get('parking_name', '')
            name = self.user_data[self.chat_id].get('login_name', '')
            surname = self.user_data[self.chat_id].get('surname', '')

            # Recupera transazioni settimanali (fees)
            fees_url = f'{base_url}/fees'
            fees_params = {'parking_id': parking_id}
            fees_response = requests.get(fees_url, params=fees_params)
            fees_response.raise_for_status()  # Lancia un'eccezione se la richiesta non va a buon fine
            fees_datalist = fees_response.json()

            # Recupera tempo trascorso settimanalmente (durations)
            durations_url = f'{base_url}/durations'
            durations_params = {'parking_id': parking_id}
            durations_response = requests.get(durations_url, params=durations_params)
            durations_response.raise_for_status()
            durations_datalist = durations_response.json()

            # Validazione delle risposte
            if not isinstance(fees_datalist, list):
                bot.sendMessage(self.chat_id, "Errore: i dati delle transazioni non sono nel formato corretto.")
                return
            if not isinstance(durations_datalist, list):
                bot.sendMessage(self.chat_id, "Errore: i dati delle durate non sono nel formato corretto.")
                return

            total_fees = 0
            user_fees = 0
            user_fees_weekly = {}
            total_durations = 0
            user_durations = 0
            user_durations_weekly = {}
            count_parkings = 0
            count_parkings_user = 0
            count_parkings_weekly_user = {}

            # Elaborazione dei dati delle transazioni
            weekly_spending = {}
            for entry in fees_datalist:
                try:
                    date = parser.parse(entry.get("time"))
                    week = date.isocalendar()[1]
                    weekly_spending[week] = weekly_spending.get(week, 0) + entry.get("fee", 0)
                    total_fees += entry.get("fee", 0)
                    count_parkings += 1
                    if entry.get("booking_code", "") == user_id:
                        user_fees += entry.get("fee", 0)
                        count_parkings_user += 1

                        count_parkings_weekly_user[week] = count_parkings_weekly_user.get(week, 0) + 1
                        user_fees_weekly[week] = user_fees_weekly.get(week, 0) + entry.get("fee", 0)
                except Exception as e:
                    print(f"Errore nel parsing della data per le transazioni: {e}")

            # Elaborazione dei dati delle durate
            weekly_durations = {}
            for entry in durations_datalist:
                try:
                    date = parser.parse(entry.get("time"))
                    week = date.isocalendar()[1]
                    duration = entry.get("duration", 0) or 0
                    weekly_durations[week] = weekly_durations.get(week, 0) + duration
                    total_durations += duration
                    if entry.get("booking_code", "") == user_id:
                        user_durations += duration
                        user_durations_weekly[week] = user_durations_weekly.get(week, 0) + duration
                except Exception as e:
                    print(f"Errore nel parsing della data per le durate: {e}")

            # Generazione dei grafici e invio
            self.plot_stats_manager(weekly_durations, weekly_spending)
            self.plot_stats_user(user_durations_weekly, user_fees_weekly, name, surname)
            self.show_stats_manager(total_durations, total_fees, count_parkings)
            self.show_stats_user(user_durations, user_fees, count_parkings_user, name, surname)
            self.show_logged_in_menu()

        except requests.exceptions.RequestException as e:
            bot.sendMessage(self.chat_id, f"Errore nella richiesta al servizio REST: {e}")
        except Exception as e:
            bot.sendMessage(self.chat_id, f"Errore generale: {e}")

    def plot_stats_manager(self, weekly_durations, weekly_spending):
        # Prepara i dati per i grafici
        max_week = max(weekly_durations.keys() | weekly_spending.keys(), default=0)
        weeks = list(range(1, max_week + 1))
        spending = [weekly_spending.get(i, 0) for i in weeks]
        time_spent = [weekly_durations.get(i, 0) for i in weeks]

        # Grafico delle spese
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(weeks, spending, marker='o', color='green', label='Spending (€)')
        ax1.set_title('Weekly Spending (€)')
        ax1.set_ylabel('Total Amount (€)')
        ax1.set_xlabel('Weeks')
        ax1.grid(True)
        ax1.legend()

        buf1 = BytesIO()
        plt.savefig(buf1, format='png')
        buf1.seek(0)
        plt.close(fig1)

        # Grafico del tempo trascorso
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        ax2.plot(weeks, time_spent, marker='o', color='red', label='Time Spent (hours)')
        ax2.set_title('Time Spent in Parking (Weekly)')
        ax2.set_ylabel('Time (hours)')
        ax2.set_xlabel('Weeks')
        ax2.grid(True)
        ax2.legend()

        buf2 = BytesIO()
        plt.savefig(buf2, format='png')
        buf2.seek(0)
        plt.close(fig2)

        # Invia i grafici a Telegram
        bot.sendPhoto(self.chat_id, buf1)
        bot.sendPhoto(self.chat_id, buf2)

    def plot_stats_user(self, user_weekly_duration, user_weekly_spending, name, surname):
        # Prepara i dati per i grafici
        max_week = max(user_weekly_duration.keys() | user_weekly_spending.keys(), default=0)
        weeks = list(range(1, max_week + 1))
        spending = [user_weekly_spending.get(i, 0) for i in weeks]
        time_spent = [user_weekly_duration.get(i, 0) for i in weeks] * 60

        # Grafico delle spese
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(weeks, spending, marker='o', color='green', label='Spending (€)')
        ax1.set_title(f'Weekly Spending of {name} {surname}(€)')
        ax1.set_ylabel('Total Amount (€)')
        ax1.set_xlabel('Weeks')
        ax1.grid(True)
        ax1.legend()

        buf1 = BytesIO()
        plt.savefig(buf1, format='png')
        buf1.seek(0)
        plt.close(fig1)

        # Grafico del tempo trascorso
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        ax2.plot(weeks, time_spent, marker='o', color='red', label='Time Spent (min)')
        ax2.set_title(f'Time Spent in Parking by {name} {surname}(Weekly)')
        ax2.set_ylabel('Time (min)')
        ax2.set_xlabel('Weeks')
        ax2.grid(True)
        ax2.legend()

        buf2 = BytesIO()
        plt.savefig(buf2, format='png')
        buf2.seek(0)
        plt.close(fig2)

        # Invia i grafici a Telegram
        bot.sendPhoto(self.chat_id, buf1)
        bot.sendPhoto(self.chat_id, buf2)

    def show_stats_user(self, tot_dur_usr, tot_fee_usr, tot_park_usr, name, surname):
        gas_price_per_litre = 1.74
        diesel_fuel_per_litre = 1.64
        avg_speed = 40
        co_2_gas = 108  # (g/km)
        co_2_diesel_fuel = 90
        diesel_fuel_avg_km_per_litre = 17
        gas_avg_km_per_litre = 13
        avg_ext_per_hour_park_fee = 1.5  # euros per hour
        bot.sendMessage(self.chat_id, f"Calculating total stats for user {name} {surname}... ")
        # STATS TO REACH OUR PARKINGS
        time_to_reach_parking_wc = 5  # min
        tot_time_to_reach_parking_wc = time_to_reach_parking_wc * tot_park_usr
        tot_km_to_reach_parking_wc = tot_park_usr * avg_speed / (60 / time_to_reach_parking_wc)
        tot_money_to_reach_parking_diesel = (
                                                    tot_km_to_reach_parking_wc / diesel_fuel_avg_km_per_litre) * diesel_fuel_per_litre
        tot_money_to_reach_parking_gas = (tot_km_to_reach_parking_wc / gas_avg_km_per_litre) * gas_price_per_litre
        co_2_to_reach_parking_diesel = tot_km_to_reach_parking_wc * co_2_diesel_fuel  # (g)
        co_2_to_reach_parking_gas = tot_km_to_reach_parking_wc * co_2_gas  # g
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

        # STATS NOT USING PARKINGS
        avg_time_to_park = 15
        tot_time_to_reach_ext_park = avg_time_to_park * tot_park_usr
        tot_km_to_reach_ext_park = tot_park_usr * avg_speed / (60 / avg_time_to_park)
        tot_money_to_reach_ext_park_diesel = (
                                                     tot_km_to_reach_ext_park / diesel_fuel_avg_km_per_litre) * diesel_fuel_per_litre
        tot_money_to_reach_ext_park_gas = (tot_km_to_reach_ext_park / gas_avg_km_per_litre) * gas_price_per_litre
        co_2_to_reach_ext_park_diesel = tot_km_to_reach_ext_park * co_2_diesel_fuel  # (g)
        co_2_to_reach_ext_park_gas = tot_km_to_reach_ext_park * co_2_gas  # g
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

        # TOTAL MONEY SPENT (INDOOR VS OUTDOOR, DIESEL VS GAS)

        tot_money_park_plus_reach_indoor_diesel = tot_money_to_reach_parking_diesel + tot_fee_usr
        tot_money_park_plus_reach_indoor_gas = tot_money_to_reach_parking_gas + tot_fee_usr
        tot_money_park_plus_reach_outdoor_diesel = tot_money_to_reach_ext_park_diesel + tot_dur_usr * avg_ext_per_hour_park_fee
        tot_money_park_plus_reach_outdoor_gas = tot_money_to_reach_ext_park_gas + tot_dur_usr * avg_ext_per_hour_park_fee
        # TODO: MAYBE PER WEEK,MONTH,YEAR?? add message
        print(
            f"Total money spent while using our services (money to reach parking plus fees) - diesel vehicles :{tot_money_park_plus_reach_indoor_diesel} euros\n")
        print(
            f"Total money spent while using our services (money to reach parking plus fees) - gas vehicles :{tot_money_park_plus_reach_indoor_gas} euros\n")
        print(
            f"Total money spent if our services were not used (money to find external parkings plus fees) - diesel vehicles :{tot_money_park_plus_reach_outdoor_diesel} euros\n")
        print(
            f"Total money spent if our services were not used (money to find external parkings plus fees) - gas vehicles :{tot_money_park_plus_reach_outdoor_gas} euros\n")

        # TOTAL CO2 EMISSIONS (INDOOR VS OUTDOOR, DIESEL VS GAS)

        tot_co2_indoor_gas = co_2_to_reach_parking_gas
        tot_co2_indoor_diesel = co_2_to_reach_parking_diesel
        tot_co2_outdoor_gas = co_2_to_reach_ext_park_diesel
        tot_co2_outdoor_diesel = co_2_to_reach_ext_park_diesel
        # TODO: MAYBE PER WEEK,MONTH,YEAR?? add message
        print(f"Total co2 emissions using our services - diesel vehicle: {tot_co2_indoor_diesel} g \n")
        print(f"Total co2 emissions using our services - gas vehicle: {tot_co2_indoor_gas} g\n")
        print(
            f"Total co2 emissions if our services were not used (co2 to find external parkings) - diesel vehicle: {tot_co2_outdoor_diesel} g\n")
        print(
            f"Total co2 emissions if our services were not used (co2 to find external parkings) - gas vehicle: {tot_co2_outdoor_gas} g\n")

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

    def show_stats_manager(self, tot_dur, tot_fee, tot_park):
        gas_price_per_litre = 1.74
        diesel_fuel_per_litre = 1.64
        avg_speed = 40
        co_2_gas = 108  # (g/km)
        co_2_diesel_fuel = 90
        diesel_fuel_avg_km_per_litre = 17
        gas_avg_km_per_litre = 13
        avg_ext_per_hour_park_fee = 1.5  # euros per hour
        bot.sendMessage(self.chat_id, f"Calculating total stats... ")
        # STATS TO REACH OUR PARKINGS
        time_to_reach_parking_wc = 5  # min
        tot_time_to_reach_parking_wc = time_to_reach_parking_wc * tot_park
        tot_km_to_reach_parking_wc = tot_park * avg_speed / (60 / time_to_reach_parking_wc)
        tot_money_to_reach_parking_diesel = (
                                                    tot_km_to_reach_parking_wc / diesel_fuel_avg_km_per_litre) * diesel_fuel_per_litre
        tot_money_to_reach_parking_gas = (tot_km_to_reach_parking_wc / gas_avg_km_per_litre) * gas_price_per_litre
        co_2_to_reach_parking_diesel = tot_km_to_reach_parking_wc * co_2_diesel_fuel  # (g)
        co_2_to_reach_parking_gas = tot_km_to_reach_parking_wc * co_2_gas  # g
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

        # STATS NOT USING PARKINGS
        avg_time_to_park = 15
        tot_time_to_reach_ext_park = avg_time_to_park * tot_park
        tot_km_to_reach_ext_park = tot_park * avg_speed / (60 / avg_time_to_park)
        tot_money_to_reach_ext_park_diesel = (
                                                     tot_km_to_reach_ext_park / diesel_fuel_avg_km_per_litre) * diesel_fuel_per_litre
        tot_money_to_reach_ext_park_gas = (tot_km_to_reach_ext_park / gas_avg_km_per_litre) * gas_price_per_litre
        co_2_to_reach_ext_park_diesel = tot_km_to_reach_ext_park * co_2_diesel_fuel  # (g)
        co_2_to_reach_ext_park_gas = tot_km_to_reach_ext_park * co_2_gas  # g
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

        # TOTAL MONEY SPENT (INDOOR VS OUTDOOR, DIESEL VS GAS)

        tot_money_park_plus_reach_indoor_diesel = tot_money_to_reach_parking_diesel + tot_fee
        tot_money_park_plus_reach_indoor_gas = tot_money_to_reach_parking_gas + tot_fee
        tot_money_park_plus_reach_outdoor_diesel = tot_money_to_reach_ext_park_diesel + tot_dur * avg_ext_per_hour_park_fee
        tot_money_park_plus_reach_outdoor_gas = tot_money_to_reach_ext_park_gas + tot_dur * avg_ext_per_hour_park_fee
        # TODO: MAYBE PER WEEK,MONTH,YEAR?? add message
        print(
            f"Total money spent while using our services (money to reach parking plus fees) - diesel vehicles :{tot_money_park_plus_reach_indoor_diesel} euros\n")
        print(
            f"Total money spent while using our services (money to reach parking plus fees) - gas vehicles :{tot_money_park_plus_reach_indoor_gas} euros\n")
        print(
            f"Total money spent if our services were not used (money to find external parkings plus fees) - diesel vehicles :{tot_money_park_plus_reach_outdoor_diesel} euros\n")
        print(
            f"Total money spent if our services were not used (money to find external parkings plus fees) - gas vehicles :{tot_money_park_plus_reach_outdoor_gas} euros\n")

        # TOTAL CO2 EMISSIONS (INDOOR VS OUTDOOR, DIESEL VS GAS)

        tot_co2_indoor_gas = co_2_to_reach_parking_gas
        tot_co2_indoor_diesel = co_2_to_reach_parking_diesel
        tot_co2_outdoor_gas = co_2_to_reach_ext_park_diesel
        tot_co2_outdoor_diesel = co_2_to_reach_ext_park_diesel
        # TODO: MAYBE PER WEEK,MONTH,YEAR?? add message
        print(f"Total co2 emissions using our services - diesel vehicle: {tot_co2_indoor_diesel} g \n")
        print(f"Total co2 emissions using our services - gas vehicle: {tot_co2_indoor_gas} g\n")
        print(
            f"Total co2 emissions if our services were not used (co2 to find external parkings) - diesel vehicle: {tot_co2_outdoor_diesel} g\n")
        print(
            f"Total co2 emissions if our services were not used (co2 to find external parkings) - gas vehicle: {tot_co2_outdoor_gas} g\n")

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


if __name__ == '__main__':

    # Inizializza il bot
    botClass = ParkingBot()
    bot = telepot.Bot(botClass.TOKEN)

    # Avvia il loop dei messaggi
    MessageLoop(bot, {
        'chat': botClass.handle_message,
        'callback_query': botClass.on_callback_query
    }).run_as_thread()

    print("Bot in esecuzione...")

    # Mantiene il programma in esecuzione
    while True:
        time.sleep(10)
