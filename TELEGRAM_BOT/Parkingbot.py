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
    """Verifica se il nome contiene solo lettere."""
    return name.isalpha()

# Funzione per validare l'identità
def is_valid_identity(id_number):
    """Verifica se l'identità è alfanumerica e di lunghezza 9."""
    return id_number.isalnum() and len(id_number) == 9

# Funzione per validare la carta di credito
def is_valid_credit_card(card_number):
    """Verifica se il numero della carta di credito è valido."""
    return card_number.isdigit() and len(card_number) == 16

# Funzione per mostrare il menu per gli utenti loggati
def show_logged_in_menu(chat_id):
    """Mostra il menu per gli utenti loggati."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Check posti liberi", callback_data='check')],
        [InlineKeyboardButton(text="Prenota un posto", callback_data='book')],
        [InlineKeyboardButton(text="Wallet", callback_data='wallet')],
        [InlineKeyboardButton(text="Logout", callback_data='logout')]
    ])
    bot.sendMessage(chat_id, "Seleziona un'opzione:", reply_markup=keyboard)

# Funzione per mostrare il menu iniziale
def show_initial_menu(chat_id):
    """Mostra il menu iniziale per utenti non loggati."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Check posti liberi", callback_data='check')],
        [InlineKeyboardButton(text="Prenota un posto", callback_data='book')],
        [InlineKeyboardButton(text="Registrati", callback_data='register')],
        [InlineKeyboardButton(text="Login", callback_data='login')]
    ])
    bot.sendMessage(chat_id, 'Benvenuto al Parking Bot! Scegli una delle seguenti opzioni:', reply_markup=keyboard)

# Funzione per chiedere all'utente di selezionare un parcheggio
def choose_parking(chat_id):
    """Chiede all'utente di selezionare un parcheggio."""
    catalog_url = settings['catalog_url'] + '/parkings'
    response = requests.get(catalog_url)
    parkings = response.json().get("parkings", [])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=parking["name"], callback_data=f"select_parking_{parking['ID']}")]
        for parking in parkings
    ])
    
    bot.sendMessage(chat_id, "Seleziona un parcheggio:", reply_markup=keyboard)

# Funzione per gestire il comando /start
def start(msg):
    """Gestisce il comando /start e mostra il menu appropriato."""
    chat_id = msg['chat']['id']
    
    if chat_id in logged_in_users and logged_in_users[chat_id]:
        show_logged_in_menu(chat_id)
    else:
        choose_parking(chat_id)  # Chiede di scegliere il parcheggio prima del menu iniziale

# Funzione per gestire le callback delle inline keyboard
def on_callback_query(msg):
    """Gestisce le callback delle inline keyboard."""
    query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')

    if query_data.startswith("select_parking_"):
        parking_id = int(query_data.split("_")[-1])
        
        # Recupero informazioni del parcheggio dal catalogo
        catalog_url = settings['catalog_url'] + '/parkings'
        response = requests.get(catalog_url)
        parkings = response.json().get("parkings", [])
        
        for parking in parkings:
            if parking["ID"] == parking_id:
                user_data[chat_id] = {
                    "parking_url": parking["url"],
                    "parking_port": parking["port"]
                }
                bot.sendMessage(chat_id, f"Parcheggio {parking['name']} selezionato!")
                show_initial_menu(chat_id)  # Mostra il menu dopo la selezione
                break
    elif query_data == 'check':
        check_free_slots({'chat': {'id': chat_id}})
        # Mostra il menu appropriato dopo l'azione
        if chat_id in logged_in_users and logged_in_users[chat_id]:
            show_logged_in_menu(chat_id)
        else:
            show_initial_menu(chat_id)
    elif query_data == 'book':
        book_slot({'chat': {'id': chat_id}})
        # Mostra il menu appropriato dopo l'azione
        if chat_id in logged_in_users and logged_in_users[chat_id]:
            show_logged_in_menu(chat_id)
        else:
            show_initial_menu(chat_id)
    elif query_data == 'register':
        register({'chat': {'id': chat_id}})
    elif query_data == 'login':
        login({'chat': {'id': chat_id}})
    elif query_data == 'logout':
        logout(chat_id)
    elif query_data == 'wallet':
        show_wallet({'chat': {'id': chat_id}})
        # Mostra il menu appropriato dopo l'azione
        if chat_id in logged_in_users and logged_in_users[chat_id]:
            show_logged_in_menu(chat_id)
        else:
            show_initial_menu(chat_id)

# Funzione per gestire il processo di registrazione
def register(msg):
    """Inizia il processo di registrazione."""
    chat_id = msg['chat']['id']
    bot.sendMessage(chat_id, "Inserisci il tuo nome:")
    user_data[chat_id] = {'state': NAME}

# Funzione per gestire il login
def login(msg):
    """Inizia il processo di login."""
    chat_id = msg['chat']['id']
    bot.sendMessage(chat_id, "Inserisci il tuo nome per il login:")
    user_data[chat_id] = {'state': 'LOGIN_NAME'}

# Funzione per gestire i messaggi ricevuti dagli utenti
def handle_message(msg):
    """Gestisce i messaggi ricevuti dagli utenti."""
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
                        del user_data[chat_id]
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
            bot.sendMessage(chat_id, "Benvenuto al Parking Bot!\nPotrai controllare i posti liberi e prenotarli direttamente da qui.\nPARCHEGGIARE NON È STATO MAI COSÌ FACILE!!\n\nPer iniziare clicca su /start")

# Funzione per verificare il login
def verify_login(chat_id):
    """Verifica le credenziali di login dell'utente."""
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

# Funzione per mostrare il wallet
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
        transactions = response_data.get('transactions', [])
        if transactions:
            message = "Le tue transazioni:\n"
            for transaction in transactions:
                duration = transaction.get('duration', 0)
                fee = transaction.get('fee', 0)
                message += f"Durata: {duration} ore, Tariffa: {fee}€\n"
            
            bot.sendMessage(chat_id, message)
        else:
            bot.sendMessage(chat_id, "Non ci sono transazioni recenti.")
    except Exception as e:
        bot.sendMessage(chat_id, f"Errore nel recupero delle transazioni: {e}")

# Funzione per inviare i dati dell'utente al catalogo
def send_user_data_to_catalog(user_data, chat_id):
    """Invia i dati dell'utente al catalogo e ritorna l'ID generato."""
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

# Funzione per gestire il logout
def logout(chat_id):
    """Gestisce il logout dell'utente."""
    if chat_id in logged_in_users:
        del logged_in_users[chat_id]
        bot.sendMessage(chat_id, "Logout avvenuto con successo.")
    else:
        bot.sendMessage(chat_id, "Non sei loggato.")
    
    show_initial_menu(chat_id)

# Funzione per controllare i posti liberi
def check_free_slots(msg):
    chat_id = msg['chat']['id']
    if chat_id not in user_data:
        choose_parking(chat_id)
        return

    parking_url = user_data[chat_id]['parking_url']
    parking_port = user_data[chat_id]['parking_port']
    url = f'http://{parking_url}:{parking_port}/check_free_slots'

    try:
        response = requests.get(url)
        response.raise_for_status()
        
        slots = json.loads(response.text)

        free_slots = [slot for slot in slots if slot.get('status') == 'free']
        
        if free_slots:
            slots_info = "\n".join([f"ID: {slot['location']}, Nome: {slot['name']}" for slot in free_slots])
            bot.sendMessage(chat_id, f'Posti liberi:\n{slots_info}')
        else:
            bot.sendMessage(chat_id, 'Nessun posto libero al momento.')
    except Exception as e:
        bot.sendMessage(chat_id, f'Errore nel recupero dei dati dei posti: {e}')

# Funzione per prenotare un posto
def book_slot(msg):
    """Prenota un posto e gestisce la scadenza della prenotazione."""
    chat_id = msg['chat']['id']
    print(chat_id)
    book_url = 'http://127.0.0.1:8098/book'
    
    try:
        if chat_id not in logged_in_users or not logged_in_users[chat_id]:
            data = {'booking_code': ''}
        else:
            data = {'booking_code': user_data[chat_id]['book_code']}

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
        
        Timer(120, expire_reservation, args=[r, booking_code]).start()

    except Exception as e:
        bot.sendMessage(chat_id, f'Errore durante la prenotazione: {e}')

# Funzione per gestire la scadenza della prenotazione
def expire_reservation(selected_device, booking_code):
    reservation_url = 'http://127.0.0.1:5001/reservation_exp'
    headers = {'Content-Type': 'application/json'}

    reservation_data = {
                        "ID": selected_device['slot_id'],
                        "name": selected_device.get('name', 'unknown'),
                        "type": selected_device.get('type', 'unknown'),
                        "location": selected_device.get('location', 'unknown'),
                        "booking_code": booking_code
    }

    req = requests.post(reservation_url, headers=headers, json=reservation_data)
    try:
        response_data = req.json()  # Prova a interpretare il contenuto come JSON
        print(f"Response JSON: {response_data}")
    except ValueError:
        # Se non è in formato JSON, stampa il contenuto come testo
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