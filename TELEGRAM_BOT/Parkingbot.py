import logging
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import time
import random
import string
from threading import Timer, Lock
from pathlib import Path
import uuid
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Usa il backend non interattivo
import matplotlib.pyplot as plt
from dateutil import parser
from io import BytesIO

class ParkingBot:
    def __init__(self, token, settings_path):
        self.bot = telepot.Bot(token)
        self.lock = Lock()
        self.user_data = {}
        self.logged_in_users = {}

        # Carica le impostazioni
        self.settings = self._load_settings(settings_path)

        # Stati per la registrazione
        self.NAME, self.SURNAME, self.IDENTITY, self.CREDIT_CARD = range(4)

    def _load_settings(self, settings_path):
        with open(settings_path, 'r') as file:
            return json.load(file)

    def start(self):
        print("Bot in esecuzione...")
        MessageLoop(self.bot, {
            'chat': self.handle_message,
            'callback_query': self.on_callback_query  
        }).run_as_thread()

        while True:
            time.sleep(10)

    def handle_message(self, msg):
        chat_id = msg['chat']['id']
        text = msg.get('text', '').strip().lower()

        if chat_id in self.user_data and 'state' in self.user_data[chat_id]:
            self.process_state(chat_id, text)
            return

        if chat_id not in self.user_data or 'parking_name' not in self.user_data[chat_id]:
            self.bot.sendMessage(chat_id, "Ciao! Che parcheggio vuoi scegliere? Una volta selezionato potrai cambiarlo solo scrivendo /parkings.")
            self.choose_parking(chat_id)
            return

        if text == '/start':
            self.show_initial_menu(chat_id)
        elif text == '/parkings':
            self.reset_parking(chat_id)
        else:
            self.bot.sendMessage(chat_id, "Non ho capito. Usa /start per iniziare o /parkings per cambiare parcheggio.")

    def process_state(self, chat_id, text):
        state = self.user_data[chat_id]['state']

        if state == self.NAME:
            if self.is_valid_name(text):
                self.user_data[chat_id]['name'] = text
                self.bot.sendMessage(chat_id, "Inserisci il tuo cognome:")
                self.user_data[chat_id]['state'] = self.SURNAME
            else:
                self.bot.sendMessage(chat_id, "Nome non valido. Inserisci un nome valido (solo lettere).")
        # Gestione di altri stati...

    def is_valid_name(self, name):
        return name.isalpha()

    def choose_parking(self, chat_id):
        catalog_url = self.settings['catalog_url'] + '/parkings'
        response = requests.get(catalog_url)

        try:
            parkings = response.json().get("parkings", [])
            if not parkings:
                self.bot.sendMessage(chat_id, "Non ci sono parcheggi disponibili al momento.")
                return

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=parking["name"], callback_data=f"select_parking_{parking['ID']}")]
                for parking in parkings
            ])
            
            self.bot.sendMessage(chat_id, "Seleziona un parcheggio:", reply_markup=keyboard)
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Errore nel recupero dei parcheggi: {e}")

    def reset_parking(self, chat_id):
        if chat_id in self.user_data:
            self.user_data[chat_id].pop('parking_name', None)
            self.user_data[chat_id].pop('parking_url', None)
            self.user_data[chat_id].pop('parking_port', None)
        self.bot.sendMessage(chat_id, "Seleziona un nuovo parcheggio:")
        self.choose_parking(chat_id)

    def on_callback_query(self, msg):
        query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')

        if query_data.startswith("select_parking_"):
            parking_id = int(query_data.split("_")[-1])
            self.handle_parking_selection(chat_id, parking_id)
        elif query_data == 'check':
            self.check_free_slots(chat_id)

    def handle_parking_selection(self, chat_id, parking_id):
        catalog_url = self.settings['catalog_url'] + '/parkings'
        response = requests.get(catalog_url)
        parkings = response.json().get("parkings", [])

        for parking in parkings:
            if parking["ID"] == parking_id:
                if chat_id not in self.user_data:
                    self.user_data[chat_id] = {}
                self.user_data[chat_id].update({
                    "parking_url": parking["url"],
                    "parking_port": parking["port"],
                    "parking_name": parking["name"]
                })

                self.bot.sendMessage(chat_id, f"Parcheggio {parking['name']} selezionato!")
                self.show_initial_menu(chat_id)
                break

    def show_initial_menu(self, chat_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Check posti liberi", callback_data='check')],
            [InlineKeyboardButton(text="Prenota un posto", callback_data='book')],
            [InlineKeyboardButton(text="Registrati", callback_data='register')],
            [InlineKeyboardButton(text="Login", callback_data='login')]
        ])
        self.bot.sendMessage(chat_id, 'Benvenuto al Parking Bot! Scegli una delle seguenti opzioni:', reply_markup=keyboard)

    def check_free_slots(self, chat_id):
        if chat_id not in self.user_data or 'parking_url' not in self.user_data[chat_id] or 'parking_port' not in self.user_data[chat_id]:
            self.bot.sendMessage(chat_id, "Per favore, seleziona prima un parcheggio.")
            self.choose_parking(chat_id)
            return

        parking_url = self.user_data[chat_id]['parking_url']
        parking_port = self.user_data[chat_id]['parking_port']
        url = f'http://{parking_url}:{parking_port}/devices'

        try:
            response = requests.get(url)
            response.raise_for_status()
            slots = response.json()
            free_slots = [device["deviceInfo"] for device in slots.get("devices", []) if device.get("deviceInfo", {}).get("status") == "free"]

            if free_slots:
                slots_info = "\n".join([f"ID: {slot['location']}, Nome: {slot['name']}" for slot in free_slots])
                self.bot.sendMessage(chat_id, f'Posti liberi:\n{slots_info}')
            else:
                self.bot.sendMessage(chat_id, 'Nessun posto libero al momento.')
        except Exception as e:
            self.bot.sendMessage(chat_id, f'Errore nel recupero dei dati dei posti: {e}')


if __name__ == "__main__":
    # Percorso al file delle impostazioni
    SETTINGS_PATH = Path(__file__).parent.absolute() / 'settings.json'

    # Token del bot Telegram
    TOKEN = 'IL_TUO_TOKEN'

    # Crea e avvia il bot
    bot = ParkingBot(TOKEN, SETTINGS_PATH)
    bot.start()
