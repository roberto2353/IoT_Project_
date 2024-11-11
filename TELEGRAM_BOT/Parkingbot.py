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
from pathlib import Path
import uuid

# Percorso al file delle impostazioni
P = Path(__file__).parent.absolute()
SETTINGS_PATH = P / 'settings.json'

# Carica le impostazioni
with open(SETTINGS_PATH, 'r') as file:
    settings = json.load(file)

# Token del bot Telegram
TOKEN = '7501377611:AAGhXNYizRlkdl3V_BGtiIK-Slb76WcxzZ8'

# Stati per la registrazione
NAME, SURNAME, IDENTITY, CREDIT_CARD = range(4)

# Dati utente e stati di login
user_data = {}
logged_in_users = {}

# Funzione per validare il nome
def is_valid_name(name):
    return name.isalpha()

def is_valid_identity(id_number):
    return id_number.isalnum() and len(id_number) == 9

def is_valid_credit_card(card_number):
    return card_number.isdigit() and len(card_number) == 16

def show_logged_in_menu(chat_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Check posti liberi", callback_data='check')],
        [InlineKeyboardButton(text="Prenota un posto", callback_data='book')],
        [InlineKeyboardButton(text="Wallet", callback_data='wallet')],
        [InlineKeyboardButton(text="Logout", callback_data='logout')]
    ])
    bot.sendMessage(chat_id, "Seleziona un'opzione:", reply_markup=keyboard)

def show_initial_menu(chat_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Check posti liberi", callback_data='check')],
        [InlineKeyboardButton(text="Prenota un posto", callback_data='book')],
        [InlineKeyboardButton(text="Registrati", callback_data='register')],
        [InlineKeyboardButton(text="Login", callback_data='login')]
    ])
    bot.sendMessage(chat_id, 'Benvenuto al Parking Bot! Scegli una delle seguenti opzioni:', reply_markup=keyboard)

def choose_parking(chat_id):
    catalog_url = settings['catalog_url'] + '/parkings'
    response = requests.get(catalog_url)
    parkings = response.json().get("parkings", [])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=parking["name"], callback_data=f"select_parking_{parking['ID']}")]
        for parking in parkings
    ])
    
    bot.sendMessage(chat_id, "Seleziona un parcheggio:", reply_markup=keyboard)

def start(msg):
    chat_id = msg['chat']['id']
    
    if chat_id in logged_in_users and logged_in_users[chat_id]:
        show_logged_in_menu(chat_id)
    else:
        choose_parking(chat_id)

def on_callback_query(msg):
    query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')

    if query_data.startswith("select_parking_"):
        parking_id = int(query_data.split("_")[-1])
        
        catalog_url = settings['catalog_url'] + '/parkings'
        response = requests.get(catalog_url)
        parkings = response.json().get("parkings", [])
        
        for parking in parkings:
            if parking["ID"] == parking_id:
                if chat_id not in user_data:
                    user_data[chat_id] = {}
                user_data[chat_id].update({
                    "parking_url": parking["url"],
                    "parking_port": parking["port"],
                    "name": parking["name"]
                })
                
                bot.sendMessage(chat_id, f"Parcheggio {parking['name']} selezionato!")
                show_initial_menu(chat_id)
                break

    elif query_data == 'check':
        check_free_slots({'chat': {'id': chat_id}})
        show_logged_in_menu(chat_id) if chat_id in logged_in_users and logged_in_users[chat_id] else show_initial_menu(chat_id)
        
    elif query_data == 'book':
        book_slot({'chat': {'id': chat_id}})
        show_logged_in_menu(chat_id) if chat_id in logged_in_users and logged_in_users[chat_id] else show_initial_menu(chat_id)
        
    elif query_data == 'register':
        register({'chat': {'id': chat_id}})
        
    elif query_data == 'login':
        login({'chat': {'id': chat_id}})
        
    elif query_data == 'logout':
        logout(chat_id)
        
    elif query_data == 'wallet':
        show_wallet({'chat': {'id': chat_id}})
        show_logged_in_menu(chat_id) if chat_id in logged_in_users and logged_in_users[chat_id] else show_initial_menu(chat_id)

def register(msg):
    chat_id = msg['chat']['id']
    bot.sendMessage(chat_id, "Inserisci il tuo nome:")
    user_data[chat_id] = {'state': NAME}

def login(msg):
    chat_id = msg['chat']['id']
    
    if chat_id in user_data and 'parking_url' in user_data[chat_id] and 'parking_port' in user_data[chat_id]:
        bot.sendMessage(chat_id, "Hai già selezionato un parcheggio. Procedi con il login.")
    else:
        bot.sendMessage(chat_id, "Prima di fare il login, seleziona un parcheggio.")
        choose_parking(chat_id)
        return
    
    bot.sendMessage(chat_id, "Inserisci il tuo nome per il login:")
    user_data[chat_id]['state'] = 'LOGIN_NAME'

def handle_message(msg):
    chat_id = msg['chat']['id']
    text = msg.get('text', '')

    if text == '/start':
        start(msg)
    else:
        if chat_id in user_data:
            state = user_data[chat_id]['state']

            if state == NAME:
                if is_valid_name(text):
                    user_data[chat_id]['name'] = text
                    bot.sendMessage(chat_id, "Inserisci il tuo cognome:")
                    user_data[chat_id]['state'] = SURNAME
                else:
                    bot.sendMessage(chat_id, "Nome non valido. Inserisci un nome valido (solo lettere):")

            elif state == SURNAME:
                if is_valid_name(text):
                    user_data[chat_id]['surname'] = text
                    bot.sendMessage(chat_id, "Inserisci il numero della tua carta di identità (es. AAAA55555):")
                    user_data[chat_id]['state'] = IDENTITY
                else:
                    bot.sendMessage(chat_id, "Cognome non valido. Inserisci un cognome valido (solo lettere):")

            elif state == IDENTITY:
                if is_valid_identity(text):
                    user_data[chat_id]['identity'] = text
                    bot.sendMessage(chat_id, "Inserisci il numero della tua carta di credito (16 cifre):")
                    user_data[chat_id]['state'] = CREDIT_CARD
                else:
                    bot.sendMessage(chat_id, "Numero di carta di identità non valido. Reinserisci il numero (9 caratteri alfanumerici):")

            elif state == CREDIT_CARD:
                if is_valid_credit_card(text):
                    user_data[chat_id]['credit_card'] = text
                    id = send_user_data_to_catalog(user_data[chat_id], chat_id)
                    if id:
                        bot.sendMessage(chat_id, f"Registrazione completata!\nUsa il tuo numero di carta di identità o il codice associato: {id} per prenotare o accedere al parcheggio.")
                        logged_in_users[chat_id] = True
                        show_initial_menu(chat_id)
                        del user_data[chat_id]['state']
                else:
                    bot.sendMessage(chat_id, "Numero di carta di credito non valido. Reinserisci il numero (16 cifre):")

            elif state == 'LOGIN_NAME':
                if is_valid_name(text):
                    user_data[chat_id]['login_name'] = text
                    bot.sendMessage(chat_id, "Inserisci il numero della tua carta di identità:")
                    user_data[chat_id]['state'] = 'LOGIN_IDENTITY'
                else:
                    bot.sendMessage(chat_id, "Nome non valido. Inserisci un nome valido.")

            elif state == 'LOGIN_IDENTITY':
                if is_valid_identity(text):
                    user_data[chat_id]['login_identity'] = text
                    verify_login(chat_id)
                else:
                    bot.sendMessage(chat_id, "Numero di carta di identità non valido.")
        else:
            bot.sendMessage(chat_id, "Benvenuto al Parking Bot!\nPotrai controllare i posti liberi e prenotarli direttamente da qui.\nPer iniziare clicca su /start")

def verify_login(chat_id):
    url = f"{settings['catalog_url']}/users"
    headers = {'Content-Type': 'application/json'}
    
    params = {
        "name": user_data[chat_id]['login_name'],
        "identity": user_data[chat_id]['login_identity']
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        users = response.json()
        for user in users.get("users", []):
            if user['name'] == params['name'] and user['identity'] == params['identity']:
                logged_in_users[chat_id] = True
                user_data[chat_id]["book_code"] = user['ID']
                bot.sendMessage(chat_id, "Login avvenuto con successo!")
                show_logged_in_menu(chat_id)
                return 

        bot.sendMessage(chat_id, "Credenziali non valide.")
    except Exception as e:
        bot.sendMessage(chat_id, f"Errore durante il login: {e}")

def show_wallet(msg):
    """Mostra il wallet dell'utente loggato."""
    chat_id = msg['chat']['id']
    if chat_id not in logged_in_users or not logged_in_users[chat_id]:
        bot.sendMessage(chat_id, "Esegui il login per vedere il tuo wallet.")
        return

    url = 'http://127.0.0.1:5001/get_booking_info'  
    headers = {'Content-Type': 'application/json'}
    data = {"booking_code": user_data[chat_id].get('book_code', '')}

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        response_data = response.json()
        print("Risposta del server per il wallet:", response_data)  # Debug: stampa la risposta del server

        if isinstance(response_data, dict) and "transactions" in response_data:
            transactions = response_data['transactions']
            message = "Le tue transazioni:\n"
            
            for transaction in transactions:
                duration = transaction.get('duration', 0)
                fee = transaction.get('fee', 0)
                message += f"Durata: {duration} ore, Tariffa: {fee}€\n"
                
            bot.sendMessage(chat_id, message if transactions else "Non ci sono transazioni recenti.")
        else:
            bot.sendMessage(chat_id, "Non ci sono transazioni recenti.")
            
    except Exception as e:
        bot.sendMessage(chat_id, f"Errore nel recupero delle transazioni: {e}")




def send_user_data_to_catalog(user_data, chat_id):
    url = settings['catalog_url'] + '/users'
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

def logout(chat_id):
    if chat_id in logged_in_users:
        del logged_in_users[chat_id]
        bot.sendMessage(chat_id, "Logout avvenuto con successo.")
    else:
        bot.sendMessage(chat_id, "Non sei loggato.")
    
    show_initial_menu(chat_id)

def check_free_slots(msg):
    chat_id = msg['chat']['id']
    
    if chat_id not in user_data or 'parking_url' not in user_data[chat_id] or 'parking_port' not in user_data[chat_id]:
        bot.sendMessage(chat_id, "Per favore, seleziona prima un parcheggio.")
        choose_parking(chat_id)
        return
    
    parking_url = user_data[chat_id]['parking_url']
    parking_port = user_data[chat_id]['parking_port']
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
            bot.sendMessage(chat_id, f'Posti liberi:\n{slots_info}')
        else:
            bot.sendMessage(chat_id, 'Nessun posto libero al momento.')
    except Exception as e:
        bot.sendMessage(chat_id, f'Errore nel recupero dei dati dei posti: {e}')

def book_slot(msg):
    chat_id = msg['chat']['id']
    book_url = 'http://127.0.0.1:8098/book'

    parking_url = user_data[chat_id]['parking_url']
    parking_port = user_data[chat_id]['parking_port']
    name_dev = user_data[chat_id]['name']
    url = f'http://{parking_url}:{parking_port}/get_best_parking'
    
    try:
        if chat_id not in logged_in_users or not logged_in_users[chat_id]:
            data = {'booking_code': '', 'url': url, 'name': name_dev}
        else:
            data = {'booking_code': user_data[chat_id]['book_code'], 'url': url, 'name': name_dev}

        headers = {'Content-Type': 'application/json'}
        book_response = requests.post(book_url, headers=headers, json=data)
        book_response.raise_for_status()

        r = book_response.json()
        slot_id = r.get('slot_id', 'bho')
        booking_code = r.get('booking_code', 'no code')

        if chat_id in logged_in_users and logged_in_users[chat_id]:
            BC = user_data[chat_id]['book_code']
            bot.sendMessage(chat_id, f'Il tuo posto prenotato è: {slot_id}. Il codice di prenotazione è: {BC}. La prenotazione è valida per 2 minuti.')
        else:
            bot.sendMessage(chat_id, f'Il tuo posto prenotato è: {slot_id}. Il codice di prenotazione è: {booking_code}. La prenotazione è valida per 2 minuti.')
        
        Timer(120, expire_reservation, args=[r, booking_code, msg]).start()

    except Exception as e:
        bot.sendMessage(chat_id, f'Errore durante la prenotazione: {e}')

def expire_reservation(selected_device, booking_code, msg):
    chat_id = msg['chat']['id']
    reservation_url = 'http://127.0.0.1:5001/reservation_exp'
    headers = {'Content-Type': 'application/json'}

    reservation_data = {
        "ID": selected_device['slot_id'],
        "name": selected_device.get('name', 'unknown'),
        "type": selected_device.get('type', 'unknown'),
        "location": selected_device.get('location', 'unknown'),
        "booking_code": booking_code,
        "name_dev": user_data[chat_id]['name']
    }

    req = requests.post(reservation_url, headers=headers, json=reservation_data)
    try:
        response_data = req.json()
        print(f"Response JSON: {response_data}")
    except ValueError:
        print(f"Response Text: {req.text}")
    except requests.exceptions.RequestException as e:
        print(f"Errore nella richiesta: {e}")

# Inizializza il bot
bot = telepot.Bot(TOKEN)

# Avvia il loop dei messaggi
MessageLoop(bot, {
    'chat': handle_message,
    'callback_query': on_callback_query  
}).run_as_thread()

print("Bot in esecuzione...")

# Mantiene il programma in esecuzione
while True:
    time.sleep(10)