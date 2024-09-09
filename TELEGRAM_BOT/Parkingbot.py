from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, ApplicationBuilder
import requests
import json
import time
from threading import Timer
import sys
import random
import string
# Percorso assoluto alla cartella del progetto
sys.path.append('/Users/alexbenedetti/Desktop/IoT_Project_')

SETTINGS_PATH = '/Users/alexbenedetti/Desktop/IoT_Project_/TAB_SLOT/settings.json'
with open(SETTINGS_PATH, 'r') as file:
    settings = json.load(file)
from DATA.event_logger import EventLogger

TOKEN = '7501377611:AAFjyciB61TVr_b5y9Bc3PAER4MeavWCP7c'

event_logger = EventLogger()


def generate_booking_code():
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return letters + numbers

# Esempio di utilizzo
booking_code = generate_booking_code()
print(booking_code)
# Gestore di aggiornamento per mostrare i posti liberi
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Benvenuto al sistema di prenotazione del parcheggio!\nUsa /check per vedere i posti liberi e /book per prenotare un posto.')

# Gestore di comando per mostrare i posti liberi
async def check_free_slots(update: Update, context: CallbackContext):
    url = settings['catalog_url'] + '/devices'
    try:
        response = requests.get(url)
        response.raise_for_status()
        slots = response.json().get('devices', [])
        free_slots = [slot for slot in slots if slot.get('status') == 'free']
        if free_slots:
            slots_info = "\n".join([f"ID: {slot['location']}, Nome: {slot['name']}" for slot in free_slots])
            await update.message.reply_text(f'Posti liberi:\n{slots_info}')
        else:
            await update.message.reply_text('Nessun posto libero al momento.')
    except Exception as e:
        await update.message.reply_text(f'Errore nel recupero dei dati dei posti: {e}')

# Gestore di comando per prenotare un posto


async def book_slot(update: Update, context: CallbackContext):
    url = settings['catalog_url'] + '/devices'
    try:
        response = requests.get(url)
        response.raise_for_status()
        slots = response.json().get('devices', [])
        free_slots = [slot for slot in slots if slot.get('status') == 'free']

        if not free_slots:
            await update.message.reply_text('Nessun posto libero al momento.')
            return

        # Seleziona automaticamente un posto libero (ad esempio il primo della lista)
        chosen_slot = free_slots[0]  # Qui scegliamo il primo posto libero
        slot_id = chosen_slot['location']
        booking_code = generate_booking_code()  # Genera il codice di prenotazione

        # URL per la prenotazione del posto selezionato
        book_url = settings['catalog_url'] + f'/book/{slot_id}'
        headers = {'Content-Type': 'application/json'}
        book_response = requests.post(book_url, headers=headers, data=json.dumps({"status": "occupied", "booking_code": booking_code}))
        book_response.raise_for_status()

        # Logga l'evento di "entrata" in InfluxDB
        event_logger.log_event(
                slot_id=booking_code,
                previous_status= "free",
                current_status= "reserved",
                duration = 0.0  # Il tempo di permanenza sarà calcolato al momento dell'uscita
            )
        await update.message.reply_text(f'Il tuo posto prenotato è: {slot_id}. Il codice di prenotazione è: {booking_code}. La prenotazione è valida per 2 minuti.')


        # Timer per liberare il posto dopo 2 minuti
        Timer(120, expire_reservation, args=[slot_id]).start()

    except Exception as e:
        await update.message.reply_text(f'Errore durante la prenotazione: {e}')

# Aggiungi la funzione di generazione del codice qui sopra o in un modulo di utilità

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
def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('check', check_free_slots))
    application.add_handler(CommandHandler('book', book_slot))
    application.run_polling()

if __name__ == '__main__':
    main()
