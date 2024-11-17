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

# Percorso al file delle impostazioni
P = Path(__file__).parent.absolute()
SETTINGS_PATH = P / 'settings.json'
with Lock():    
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
        [InlineKeyboardButton(text="Visualizza Grafici", callback_data='show_graphs')],
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
    print("Risposta del catalogo per /parkings:", response.text)  # Log del risultato

    try:
        parkings = response.json().get("parkings", [])
        if not parkings:
            bot.sendMessage(chat_id, "Non ci sono parcheggi disponibili al momento.")
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=parking["name"], callback_data=f"select_parking_{parking['ID']}")]
            for parking in parkings
        ])
        
        bot.sendMessage(chat_id, "Seleziona un parcheggio:", reply_markup=keyboard)
    except Exception as e:
        bot.sendMessage(chat_id, f"Errore nel recupero dei parcheggi: {e}")
def start(msg):
    chat_id = msg['chat']['id']
    if chat_id not in user_data or 'parking_name' not in user_data[chat_id]:
        bot.sendMessage(chat_id, "Ciao! Che parcheggio vuoi scegliere? Una volta selezionato potrai cambiarlo solo scrivendo /parkings.")
        choose_parking(chat_id)
    else:
        bot.sendMessage(chat_id, f"Parcheggio selezionato: {user_data[chat_id]['parking_name']}.")
        if chat_id in logged_in_users and logged_in_users[chat_id]:
            show_logged_in_menu(chat_id)
        else:
            show_initial_menu(chat_id)

def reset_parking(msg):
    chat_id = msg['chat']['id']
    if chat_id in user_data:
        user_data[chat_id].pop('parking_name', None)
        user_data[chat_id].pop('parking_url', None)
        user_data[chat_id].pop('parking_port', None)
    bot.sendMessage(chat_id, "Seleziona un nuovo parcheggio:")
    choose_parking(chat_id)

def show_graphs(msg):    
    chat_id = msg['chat']['id']
    if chat_id not in logged_in_users or not logged_in_users[chat_id]:
        bot.sendMessage(chat_id, "Esegui il login per visualizzare i grafici.")
        return
    
    try:
        # URL di base per il servizio REST
        base_url = 'http://127.0.0.1:5001'

        # Ottieni ID utente
        user_id = user_data[chat_id].get('ID', '')

        # Recupera transazioni settimanali (fees)
        fees_url = f'{base_url}/fees'
        fees_params = {'parking_id': user_id}
        fees_response = requests.get(fees_url, params=fees_params)
        fees_data = fees_response.json()

        # Recupera tempo trascorso settimanalmente (durations)
        durations_url = f'{base_url}/durations'
        durations_params = {'parking_id': user_id}
        durations_response = requests.get(durations_url, params=durations_params)
        durations_data = durations_response.json()

        # Gestione degli errori nelle risposte
        if isinstance(fees_data, dict) and 'error' in fees_data:
            bot.sendMessage(chat_id, "Errore durante il recupero dei dati delle transazioni.")
            return
        if isinstance(durations_data, dict) and 'error' in durations_data:
            bot.sendMessage(chat_id, "Errore durante il recupero dei dati delle durate.")
            return

        # Trasforma i dati grezzi nei formati richiesti
        # Aggrega i dati settimanalmente
        weekly_transactions = {}
        weekly_spending = {}
        for entry in fees_data:
            try:
                # Usa il parser per gestire correttamente la data con "T" e "Z"
                date = parser.parse(entry.get("time"))  # Metodo 1
                week = date.isocalendar()[1]  # Ottieni la settimana dell'anno
                weekly_transactions[week] = weekly_transactions.get(week, 0) + 1
                weekly_spending[week] = weekly_spending.get(week, 0) + entry.get("fee", 0)
            except Exception as e:
                print(f"Errore nel parsing della data per le transazioni: {e}")

        weekly_durations = {}
        for entry in durations_data:
            try:
                # Usa il parser per gestire correttamente la data con "T" e "Z"
                date = parser.parse(entry.get("time"))  # Metodo 1
                week = date.isocalendar()[1]
                weekly_durations[week] = weekly_durations.get(week, 0) + entry.get("duration", 0)
            except Exception as e:
                print(f"Errore nel parsing della data per le durate: {e}")

        # Prepara i dati per i grafici
        max_week = max(weekly_transactions.keys() | weekly_durations.keys() | weekly_spending.keys(), default=0)
        weeks = [f"Settimana {i}" for i in range(1, max_week + 1)]
        transactions = [weekly_transactions.get(i, 0) for i in range(1, max_week + 1)]
        spending = [weekly_spending.get(i, 0) for i in range(1, max_week + 1)]
        time_spent = [weekly_durations.get(i, 0) for i in range(1, max_week + 1)]

        # Genera i grafici
        fig, axs = plt.subplots(3, 1, figsize=(10, 15))
        
        axs[0].bar(weeks, transactions, color='blue')
        axs[0].set_title('Transazioni Settimanali')
        axs[0].set_ylabel('Numero di Transazioni')
        axs[0].tick_params(axis='x', rotation=45)

        axs[1].bar(weeks, spending, color='green')
        axs[1].set_title('Spese Settimanali (€)')
        axs[1].set_ylabel('Spese Totali (€)')
        axs[1].tick_params(axis='x', rotation=45)

        axs[2].bar(weeks, time_spent, color='red')
        axs[2].set_title('Tempo Trascorso al Parcheggio (Settimane)')
        axs[2].set_ylabel('Tempo (ore)')
        axs[2].tick_params(axis='x', rotation=45)

        plt.tight_layout()

        # Salva il grafico in un oggetto BytesIO per l'invio a Telegram
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        # Invia il grafico a Telegram
        bot.sendPhoto(chat_id, buf)
        
    except Exception as e:
        bot.sendMessage(chat_id, f"Errore nel recupero dei dati: {e}")
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
                    "parking_name": parking["name"]
                })
                
                bot.sendMessage(chat_id, f"Parcheggio {parking['name']} selezionato!")
                
                # Mostra il menu iniziale o riprendi il processo corrente
                if 'state' in user_data[chat_id] and user_data[chat_id]['state'] == 'LOGIN_NAME':
                    bot.sendMessage(chat_id, "Inserisci il tuo nome per il login:")
                else:
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

    elif query_data == 'show_graphs':
        show_graphs({'chat': {'id': chat_id}})

def register(msg):
    chat_id = msg['chat']['id']
    bot.sendMessage(chat_id, "Inserisci il tuo nome:")
    user_data[chat_id] = {'state': NAME}

def login(msg):
    chat_id = msg['chat']['id']
    # Verifica se il parcheggio è stato selezionato DECIDIDIAMO SE SIA NECESSARIO???????
    #if chat_id not in user_data or 'parking_name' not in user_data[chat_id]:
    #    bot.sendMessage(chat_id, "Prima di fare il login, seleziona un parcheggio.")
    #    choose_parking(chat_id)
    #    return
    
    # Se il parcheggio è selezionato, avvia il processo di login
    bot.sendMessage(chat_id, "Inserisci il tuo nome per il login:")
    user_data[chat_id]['state'] = 'LOGIN_NAME'
def handle_message(msg):
    chat_id = msg['chat']['id']
    text = msg.get('text', '').strip().lower()

    # Se l'utente è in uno stato di registrazione, non chiedere il parcheggio
    if chat_id in user_data and 'state' in user_data[chat_id]:
        process_state(chat_id, text)
        return

    # Se l'utente non ha un parcheggio selezionato, chiedilo
    if chat_id not in user_data or 'parking_name' not in user_data[chat_id]:
        bot.sendMessage(chat_id, "Ciao! Che parcheggio vuoi scegliere? Una volta selezionato potrai cambiarlo solo scrivendo /parkings.")
        choose_parking(chat_id)
        return

    # Comandi principali
    if text == '/start':
        start(msg)
    elif text == '/parkings':
        reset_parking(msg)
    else:
        bot.sendMessage(chat_id, "Non ho capito. Usa /start per iniziare o /parkings per cambiare parcheggio.")
def process_state(chat_id, text):
    state = user_data[chat_id]['state']

    if state == NAME:
        if is_valid_name(text):
            user_data[chat_id]['name'] = text
            bot.sendMessage(chat_id, "Inserisci il tuo cognome:")
            user_data[chat_id]['state'] = SURNAME
        else:
            bot.sendMessage(chat_id, "Nome non valido. Inserisci un nome valido (solo lettere).")

    elif state == SURNAME:
        if is_valid_name(text):
            user_data[chat_id]['surname'] = text
            bot.sendMessage(chat_id, "Inserisci il numero della tua carta di identità (es. AAAA55555):")
            user_data[chat_id]['state'] = IDENTITY
        else:
            bot.sendMessage(chat_id, "Cognome non valido. Inserisci un cognome valido (solo lettere).")

    elif state == IDENTITY:
        if is_valid_identity(text):
            user_data[chat_id]['identity'] = text
            bot.sendMessage(chat_id, "Inserisci il numero della tua carta di credito (16 cifre):")
            user_data[chat_id]['state'] = CREDIT_CARD
        else:
            bot.sendMessage(chat_id, "Numero di carta di identità non valido. Reinserisci il numero (9 caratteri alfanumerici).")

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
            bot.sendMessage(chat_id, "Numero di carta di credito non valido. Reinserisci il numero (16 cifre).")

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
            user_data[chat_id]['state'] = 'LOGIN_NAME'  # Torna allo stato di inserimento nome

    else:
        bot.sendMessage(chat_id, "Benvenuto al Parking Bot!\nPotrai controllare i posti liberi e prenotarli direttamente da qui.\nPer iniziare clicca su /start")

def verify_login(chat_id):
    url = f"{settings['catalog_url']}/users"
    headers = {'Content-Type': 'application/json'}
    
    # Normalizza i dati forniti dall'utente
    login_name = user_data[chat_id].get('login_name', '').strip().lower()
    login_identity = user_data[chat_id].get('login_identity', '').strip().upper()  # Converti in maiuscolo

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        users = response.json().get("users", [])
        print("Dati ricevuti dal catalogo:", users)  # Debug

        # Log temporaneo per verificare il confronto
        print(f"Login Name Inserito: {login_name}, Login Identity Inserito: {login_identity}")

        # Cerca l'utente corrispondente
        for user in users:
            catalog_name = user['name'].strip().lower()  # Normalizza il nome dal catalogo
            catalog_identity = user['identity'].strip().upper()  # Normalizza l'identità dal catalogo

            print(f"Confrontando con: Name={catalog_name}, Identity={catalog_identity}")

            if catalog_name == login_name and catalog_identity == login_identity:
                logged_in_users[chat_id] = True
                user_data[chat_id]["book_code"] = user['ID']
                bot.sendMessage(chat_id, "Login avvenuto con successo!")
                show_logged_in_menu(chat_id)
                return 

        # Se non corrisponde
        bot.sendMessage(chat_id, "Credenziali non valide. Riprova.")
        user_data[chat_id]['state'] = None
        show_initial_menu(chat_id)

    except requests.exceptions.RequestException as e:
        bot.sendMessage(chat_id, f"Errore durante il login: {e}")
        user_data[chat_id]['state'] = None
        show_initial_menu(chat_id)

def show_wallet(msg):
    """Mostra solo le transazioni individuali del wallet dell'utente loggato."""
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

        # Verifica se ci sono transazioni individuali
        if "transactions" in response_data and isinstance(response_data["transactions"], list):
            transactions = response_data["transactions"]
            message = "Le tue transazioni recenti:\n"

            for transaction in transactions:
                slot_id = transaction.get("slot_id", "N/A")
                duration = round(transaction.get("duration", 0), 2)
                fee = round(transaction.get("fee", 0), 2)
                time = transaction.get("time", "N/A")  # Facoltativo
                message += f"Posto: {slot_id}, Durata: {duration} ore, Tariffa: {fee} €, Data: {time}\n"

            bot.sendMessage(chat_id, message)
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

    # Controllo se l'utente ha selezionato un parcheggio
    parking_url = user_data.get(chat_id, {}).get('parking_url')
    parking_port = user_data.get(chat_id, {}).get('parking_port')
    name_dev = user_data.get(chat_id, {}).get('name', 'guest')  # Nome predefinito per utenti non registrati

    if not parking_url or not parking_port:
        bot.sendMessage(chat_id, "Errore: Devi selezionare un parcheggio prima di prenotare.")
        return

    url = f'http://{parking_url}:{parking_port}/get_best_parking'

    try:
        # Crea il payload per la richiesta
        if chat_id not in logged_in_users or not logged_in_users[chat_id]:
            data = {'booking_code': '', 'url': url, 'name': name_dev}
        else:
            data = {'booking_code': user_data[chat_id].get('book_code', ''), 'url': url, 'name': name_dev}

        headers = {'Content-Type': 'application/json'}
        book_response = requests.post(book_url, headers=headers, json=data)
        book_response.raise_for_status()

        r = book_response.json()
        slot_id = r.get('slot_id', 'N/A')
        booking_code = r.get('booking_code', 'N/A')

        if chat_id in logged_in_users and logged_in_users[chat_id]:
            BC = user_data[chat_id].get('book_code', 'N/A')
            bot.sendMessage(chat_id, f"Il tuo posto prenotato è: {slot_id}. Il codice di prenotazione è: {BC}. La prenotazione è valida per 2 minuti.")
        else:
            bot.sendMessage(chat_id, f"Il tuo posto prenotato è: {slot_id}. Il codice di prenotazione è: {booking_code}. La prenotazione è valida per 2 minuti.")

        # Timer per la scadenza della prenotazione
        Timer(120, expire_reservation, args=[r, booking_code, msg]).start()

    except requests.exceptions.RequestException as e:
        bot.sendMessage(chat_id, f"Errore durante la comunicazione con il sistema di prenotazione: {e}")
    except Exception as e:
        bot.sendMessage(chat_id, f"Errore durante la prenotazione: {e}")


def expire_reservation(selected_device, booking_code, msg):
    chat_id = msg['chat']['id']
    reservation_url = 'http://127.0.0.1:5001/reservation_exp'
    headers = {'Content-Type': 'application/json'}

    # Verifica che 'name_dev' esista in user_data
    name_dev = user_data.get(chat_id, {}).get('name_dev', 'guest')  # Default 'guest' se non registrato

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