import telepot
from telepot.loop import MessageLoop
import requests
import json
import time
from threading import Timer
import sys
import random
import string
from pathlib import Path
import uuid

#sys.path.append('/Users/alexbenedetti/Desktop/IoT_Project_')

P = Path(__file__).parent.absolute()
SETTINGS_PATH = P / 'settings.json'

with open(SETTINGS_PATH, 'r') as file:
    settings = json.load(file)

#from DATA.event_logger import EventLogger

TOKEN = '7501377611:AAFjyciB61TVr_b5y9Bc3PAER4MeavWCP7c'
#event_logger = EventLogger()

# States for the conversation
NAME, SURNAME, IDENTITY, CREDIT_CARD = range(4)

# User data tracking
user_data = {}

def generate_booking_code():
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return letters + numbers

booking_code = generate_booking_code()
#print(booking_code)

def is_valid_name(name):
    return name.isalpha()

def is_valid_identity(id_number):
    return id_number.isalnum() and len(id_number) == 9

def is_valid_credit_card(card_number):
    return card_number.isdigit() and len(card_number) == 16

def start(msg):
    chat_id = msg['chat']['id']
    bot.sendMessage(chat_id, 'Benvenuto al sistema di prenotazione del parcheggio!\nUsa /check per vedere i posti liberi e /book per prenotare un posto.\nUsa /register per iniziare il processo di registrazione.')

def register(msg):
    chat_id = msg['chat']['id']
    bot.sendMessage(chat_id, "Inserisci il tuo nome:")
    user_data[chat_id] = {'state': NAME}

def handle_message(msg):
    chat_id = msg['chat']['id']
    text = msg.get('text', '')

    # Controllo se è un comando
    if text.startswith('/'):
        if text == '/register':
            register(msg)
        elif text == '/check':
            check_free_slots(msg)
        elif text == '/book':
            book_slot(msg)
        elif text == '/start':
            start(msg)
        else:
            bot.sendMessage(chat_id, "Comando non riconosciuto.")
    else:
        # Gestione del messaggio utente durante la registrazione
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
                    bot.sendMessage(chat_id, "Registrazione completata!")
                    send_user_data_to_catalog(user_data[chat_id])
                    del user_data[chat_id]  # Registration complete, clean up
                else:
                    bot.sendMessage(chat_id, "Numero di carta di credito non valido. Reinserisci il numero (16 cifre):")
        else:
            bot.sendMessage(chat_id, "Usa /register per iniziare la registrazione.")

def send_user_data_to_catalog(user_data):
    url = settings['catalog_url'] + '/users'
    headers = {'Content-Type': 'application/json'}
    user_info = {
        "ID": str(uuid.uuid4()),  # Generate a unique ID for the user
        "name": user_data['name'],
        "surname": user_data['surname'],
        "identity": user_data['identity'],
        "credit_card": user_data['credit_card']
    }

    try:
        # Send the POST request
        response = requests.post(url, headers=headers, json=user_info)
        
        # Print the status code for debugging
        print(f"Status code: {response.status_code}")
        
        # Check if the response was successful
        response.raise_for_status()

        # Check the content type to decide how to handle the response
        if 'application/json' in response.headers.get('Content-Type', ''):
            # Parse as JSON if content type is JSON
            print(f"User data successfully sent to catalog: {response.json()}")
        else:
            # Print plain text response if it's not JSON
            print(f"Response content: {response.text}")
    
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as err:
        print(f"Failed to send user data to catalog: {err}")
    except json.JSONDecodeError as json_err:
        print(f"Error decoding the JSON response: {json_err}")



def check_free_slots(msg):
    chat_id = msg['chat']['id']
    url = 'http://127.0.0.1:5000/'  # URL dell'adaptor esposto da CherryPy

    try:
        # Effettua una richiesta GET all'adaptor per ottenere i dispositivi
        response = requests.get(url)
        response.raise_for_status()
        
        # Decodifica la risposta come stringa JSON
        slots = json.loads(response.text)

        print(response.text)

        
        # Filtra i dispositivi con stato 'free'
        free_slots = [slot for slot in slots if slot.get('status') == 'free']
        
        if free_slots:
            slots_info = "\n".join([f"ID: {slot['location']}, Nome: {slot['name']}" for slot in free_slots])
            bot.sendMessage(chat_id, f'Posti liberi:\n{slots_info}')
        else:
            bot.sendMessage(chat_id, 'Nessun posto libero al momento.')
    except Exception as e:
        bot.sendMessage(chat_id, f'Errore nel recupero dei dati dei posti: {e}')


def book_slot(msg):
    chat_id = msg['chat']['id']
    
    # URL del metodo CherryPy per la prenotazione
    book_url = 'http://127.0.0.1:8098/book'
    
    try:
        # Effettua una richiesta POST al metodo CherryPy 'book'
        headers = {'Content-Type': 'application/json'}
        book_response = requests.post(book_url, headers=headers)
        book_response.raise_for_status()

        # Ottieni i dati della risposta
        r = book_response.json()

        # Prendi i dati dalla risposta
        slot_id = r.get('slot_id', 'bho')
        booking_code = r.get('booking_code', 'no code')

        if 'message' in r:
            print(f"Messaggio ricevuto dal server: {r['message']}")
        
        # Invia il messaggio di conferma prenotazione all'utente tramite bot
        bot.sendMessage(chat_id, f'Il tuo posto prenotato è: {slot_id}. Il codice di prenotazione è: {booking_code}. La prenotazione è valida per 2 minuti.')

        # Imposta un timer per scadere la prenotazione dopo 2 minuti
        Timer(120, expire_reservation, args=[slot_id, booking_code]).start()

    except Exception as e:
        bot.sendMessage(chat_id, f'Errore durante la prenotazione: {e}')


def expire_reservation(slot_id, booking_code):
    url = settings['catalog_url'] + f'/expire/{slot_id}'
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({"booking_code": booking_code})
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        print(f'La prenotazione per il posto {slot_id} con codice {booking_code} è scaduta.')
    except Exception as e:
        print(f'Errore nel scadere la prenotazione per il posto {slot_id} con codice {booking_code}: {e}')

bot = telepot.Bot(TOKEN)

MessageLoop(bot, {
    'chat': handle_message,
    'text': {
        '/start': start,
        '/check': check_free_slots,
        '/book': book_slot,
        '/register': register
    }
}).run_as_thread()

while True:
    time.sleep(10)
