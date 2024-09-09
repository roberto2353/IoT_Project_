from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, ApplicationBuilder, ConversationHandler, MessageHandler,Filters

import requests
import json
import time
from threading import Timer
import sys
import random
import string
import re  # Import per espressioni regolari

# Percorso assoluto alla cartella del progetto
sys.path.append('/Users/alexbenedetti/Desktop/IoT_Project_')

SETTINGS_PATH = '/Users/alexbenedetti/Desktop/IoT_Project_/TAB_SLOT/settings.json'
with open(SETTINGS_PATH, 'r') as file:
    settings = json.load(file)

TOKEN = '7501377611:AAFjyciB61TVr_b5y9Bc3PAER4MeavWCP7c'

NAME, SURNAME, IDENTITY, CREDIT_CARD = range(4)  # Stati per la conversazione

def generate_booking_code():
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return letters + numbers

# Funzioni di validazione
def validate_identity(id_number):
    return re.match(r'^[A-Z]{4}\d{5}$', id_number) is not None

def validate_credit_card(card_number):
    return re.match(r'^\d{16}$', card_number) is not None

# Handler di start e callback per il comando di registrazione
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        'Benvenuto al sistema di prenotazione del parcheggio!\n'
        'Usa /check per vedere i posti liberi, /book per prenotare un posto.\n'
        'Per registrarti, usa /register.'
    )

async def register(update: Update, context: CallbackContext):
    await update.message.reply_text("Per favore, inviami il tuo nome.")
    return NAME

async def input_name(update: Update, context: CallbackContext):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Ora, il tuo cognome.")
    return SURNAME

async def input_surname(update: Update, context: CallbackContext):
    context.user_data['surname'] = update.message.text
    await update.message.reply_text("Inviami il numero della tua carta di identità (formato: AAAA55555).")
    return IDENTITY

async def input_identity(update: Update, context: CallbackContext):
    identity = update.message.text
    if validate_identity(identity):
        context.user_data['identity'] = identity
        await update.message.reply_text("Infine, il numero della tua carta di credito (16 cifre).")
        return CREDIT_CARD
    else:
        await update.message.reply_text("Formato non valido. Riprova.")
        return IDENTITY

async def input_credit_card(update: Update, context: CallbackContext):
    credit_card = update.message.text
    if validate_credit_card(credit_card):
        context.user_data['credit_card'] = credit_card
        await update.message.reply_text("Registrazione completata! Ora puoi usare /book per prenotare senza ulteriori dettagli.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Numero di carta non valido. Riprova.")
        return CREDIT_CARD

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('Registrazione annullata.')
    return ConversationHandler.END

# Handler aggiuntivi per il controllo dei posti e la prenotazione
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

        chosen_slot = free_slots[0]  # Seleziona automaticamente il primo posto libero
        slot_id = chosen_slot['location']
        booking_code = generate_booking_code()

        book_url = settings['catalog_url'] + f'/book/{slot_id}'
        headers = {'Content-Type': 'application/json'}
        book_response = requests.post(book_url, headers=headers, data=json.dumps({"status": "occupied", "booking_code": booking_code}))
        book_response.raise_for_status()

        event_logger.log_event(slot_id=slot_id, previous_status="free", current_status="reserved", duration=0.0)
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
            NAME: [MessageHandler(Filters.text & ~Filters.command, input_name)],
            SURNAME: [MessageHandler(Filters.text & ~Filters.command, input_surname)],
            IDENTITY: [MessageHandler(Filters.text & ~Filters.command, input_identity)],
            CREDIT_CARD: [MessageHandler(Filters.text & ~Filters.command, input_credit_card)]
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