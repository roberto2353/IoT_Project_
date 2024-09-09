from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, ApplicationBuilder, MessageHandler, ConversationHandler
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

NAME, SURNAME, IDENTITY, CREDIT_CARD = range(4)  # Stati per la conversazione

def generate_booking_code():
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return letters + numbers

booking_code = generate_booking_code()
print(booking_code)

def is_valid_name(name):
    return name.isalpha()

def is_valid_identity(id_number):
    return id_number.isalnum() and len(id_number) == 9

def is_valid_credit_card(card_number):
    return card_number.isdigit() and len(card_number) == 16

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Benvenuto al sistema di prenotazione del parcheggio!\nUsa /check per vedere i posti liberi e /book per prenotare un posto.\nUsa /register per iniziare il processo di registrazione.')

async def register(update: Update, context: CallbackContext):
    await update.message.reply_text("Inserisci il tuo nome:")
    return NAME

async def input_name(update: Update, context: CallbackContext):
    name = update.message.text
    if is_valid_name(name):
        context.user_data['name'] = name
        await update.message.reply_text("Inserisci il tuo cognome:")
        return SURNAME
    else:
        await update.message.reply_text("C'è qualcosa di errato, reinserisci il tuo nome (solo lettere):")
        return NAME

async def input_surname(update: Update, context: CallbackContext):
    surname = update.message.text
    if is_valid_name(surname):
        context.user_data['surname'] = surname
        await update.message.reply_text("Inserisci il numero della tua carta di identità (es. AAAA55555):")
        return IDENTITY
    else:
        await update.message.reply_text("C'è qualcosa di errato, reinserisci il tuo cognome (solo lettere):")
        return SURNAME

async def input_identity(update: Update, context: CallbackContext):
    id_number = update.message.text
    if is_valid_identity(id_number):
        context.user_data['identity'] = id_number
        await update.message.reply_text("Inserisci il numero della tua carta di credito (16 cifre):")
        return CREDIT_CARD
    else:
        await update.message.reply_text("C'è qualcosa di errato, reinserisci il numero della tua carta di identità (9 caratteri alfanumerici):")
        return IDENTITY

async def input_credit_card(update: Update, context: CallbackContext):
    card_number = update.message.text
    if is_valid_credit_card(card_number):
        context.user_data['credit_card'] = card_number
        await update.message.reply_text("Registrazione completata!")
        return ConversationHandler.END
    else:
        await update.message.reply_text("C'è qualcosa di errato, reinserisci il numero della tua carta di credito (16 cifre numeriche):")
        return CREDIT_CARD

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('Registrazione annullata.')
    return ConversationHandler.END

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

        chosen_slot = free_slots[0]
        slot_id = chosen_slot['location']
        booking_code = generate_booking_code()

        book_url = settings['catalog_url'] + f'/book/{slot_id}'
        headers = {'Content-Type': 'application/json'}
        book_response = requests.post(book_url, headers=headers, data=json.dumps({"status": "occupied", "booking_code": booking_code}))
        book_response.raise_for_status()

        event_logger.log_event(slot_id=booking_code, previous_status="free", current_status="reserved", duration=0.0)
        await update.message.reply_text(f'Il tuo posto prenotato è: {slot_id}. Il codice di prenotazione è: {booking_code}. La prenotazione è valida per 2 minuti.')

        Timer(120, expire_reservation, args=[slot_id, booking_code]).start()

    except Exception as e:
        await update.message.reply_text(f'Errore durante la prenotazione: {e}')

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
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            NAME: [MessageHandler(None, input_name)],
            SURNAME: [MessageHandler(None, input_surname)],
            IDENTITY: [MessageHandler(None, input_identity)],
            CREDIT_CARD: [MessageHandler(None, input_credit_card)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('check', check_free_slots))
    application.add_handler(CommandHandler('book', book_slot))
    application.run_polling()

if __name__ == '__main__':
    main()
