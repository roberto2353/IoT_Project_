import telepot
from telepot.loop import MessageLoop
import requests
import json
import time
from threading import Timer
import sys
import random
import string

# Percorso assoluto alla cartella del progetto
sys.path.append('"C:/Users/kevin/Documents/PoliTo/ProgrammingIOT/IoT_Project_"')

SETTINGS_PATH = 'C:/Users/kevin/Documents/PoliTo/ProgrammingIOT/IoT_Project_/TAB_SLOT/settings.json'
with open(SETTINGS_PATH, 'r') as file:
    settings = json.load(file)
#from DATA.event_logger import EventLogger

TOKEN = '7501377611:AAFjyciB61TVr_b5y9Bc3PAER4MeavWCP7c'

#event_logger = EventLogger()

# Funzione per generare un codice di prenotazione
def generate_booking_code():
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return letters + numbers

# Esempio di utilizzo
booking_code = generate_booking_code()
print(booking_code)

# Funzione per gestire il comando /start
def start(msg):
    chat_id = msg['chat']['id']
    bot.sendMessage(chat_id, 'Benvenuto al sistema di prenotazione del parcheggio!\nUsa /check per vedere i posti liberi e /book per prenotare un posto.')

# Funzione per gestire il comando /check per mostrare i posti liberi
def check_free_slots(msg):
    chat_id = msg['chat']['id']
    url = settings['catalog_url'] + '/devices'
    try:
        response = requests.get(url)
        response.raise_for_status()
        slots = response.json().get('devices', [])
        free_slots = [slot for slot in slots if slot.get('status') == 'free']
        if free_slots:
            slots_info = "\n".join([f"ID: {slot['location']}, Nome: {slot['name']}" for slot in free_slots])
            bot.sendMessage(chat_id, f'Posti liberi:\n{slots_info}')
        else:
            bot.sendMessage(chat_id, 'Nessun posto libero al momento.')
    except Exception as e:
        bot.sendMessage(chat_id, f'Errore nel recupero dei dati dei posti: {e}')

# Funzione per gestire il comando /book per prenotare un posto
def book_slot(msg):
    chat_id = msg['chat']['id']
    url = settings['catalog_url'] + '/devices'
    try:
        response = requests.get(url)
        response.raise_for_status()
        slots = response.json().get('devices', [])
        free_slots = [slot for slot in slots if slot.get('status') == 'free']

        if not free_slots:
            bot.sendMessage(chat_id, 'Nessun posto libero al momento.')
            return

        # Seleziona automaticamente un posto libero
        chosen_slot = free_slots[0]
        slot_id = chosen_slot['location']
        booking_code = generate_booking_code()

        # URL per la prenotazione del posto selezionato
        book_url = 'http://127.0.0.1:8088/book/'
        headers = {'Content-Type': 'application/json'}
        data = json.dumps({"slot_id": slot_id, "status": "occupied", "booking_code": booking_code})
        book_response = requests.post(book_url, headers=headers, data=data)
        book_response.raise_for_status()

        # Logga l'evento di "entrata"
        # event_logger.log_event(
        #     slot_id=booking_code,
        #     previous_status="free",
        #     current_status="reserved",
        #     duration=0.0  # Il tempo sarà calcolato al momento dell'uscita
        # )

        bot.sendMessage(chat_id, f'Il tuo posto prenotato è: {slot_id}. Il codice di prenotazione è: {booking_code}. La prenotazione è valida per 2 minuti.')

        # Timer per liberare il posto dopo 2 minuti
        Timer(120, expire_reservation, args=[slot_id, booking_code]).start()

    except Exception as e:
        bot.sendMessage(chat_id, f'Errore durante la prenotazione: {e}')

# Funzione per scadere la prenotazione
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

# Funzione per gestire i messaggi in arrivo
def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    if content_type == 'text':
        command = msg['text']
        if command == '/start':
            start(msg)
        elif command == '/check':
            check_free_slots(msg)
        elif command == '/book':
            book_slot(msg)
        else:
            bot.sendMessage(chat_id, 'Comando non supportato.')

# Funzione principale
if __name__ == '__main__':
    bot = telepot.Bot(TOKEN)
    MessageLoop(bot, handle).run_as_thread()
    print('Listening ...')

    while True:
        time.sleep(10)
