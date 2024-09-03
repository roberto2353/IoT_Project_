from telegram import Update, Bot
from telegram.ext import CommandHandler, CallbackContext, ApplicationBuilder
import requests
import json
import time
from threading import Timer


SETTINGS_PATH = '/Users/alexbenedetti/Desktop/IoT_Project_/TAB_SLOT/settings.json'
with open(SETTINGS_PATH, 'r') as file:
    settings = json.load(file)


TOKEN = '7501377611:AAFjyciB61TVr_b5y9Bc3PAER4MeavWCP7c'  

# Gestore di aggiornamento per mostrare i posti liberi
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Benvenuto al sistema di prenotazione del parcheggio!\nUsa /check per vedere i posti liberi e /book <posto_id> per prenotare un posto.')

# Gestore di comando per mostrare i posti liberi
async def check_free_slots(update: Update, context: CallbackContext):
    url = settings['catalog_url'] + '/devices'
    try:
        response = requests.get(url)
        response.raise_for_status()
        slots = response.json().get('devices', [])

        
        print(f"Risposta del server: {slots}")

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
    try:
        slot_id = context.args[0]  # ID del posto passato dall'utente
        url = settings['catalog_url'] + f'/book/{slot_id}'
        headers = {'Content-Type': 'application/json'}
        data = json.dumps({"status": "occupied"})  # Ensure you're sending data

        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()

        await update.message.reply_text(f'Il posto {slot_id} è stato prenotato con successo per 2 minuti!')

        #  timer per togliere la prenotazione dopo 2 minuti
        Timer(120, expire_reservation, args=[slot_id]).start()

    except IndexError:
        await update.message.reply_text('Per favore specifica un ID di posto da prenotare. Uso: /book <posto_id>')
    except Exception as e:
        await update.message.reply_text(f'Errore durante la prenotazione: {e}')


# togliere una prenotazione
def expire_reservation(slot_id):
    url = settings['catalog_url'] + f'/expire/{slot_id}'
    try:
        response = requests.post(url)
        response.raise_for_status()
        print(f'La prenotazione per il posto {slot_id} è scaduta.')
    except Exception as e:
        print(f'Errore nel scadere la prenotazione per il posto {slot_id}: {e}')

def main():
    
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('check', check_free_slots))
    application.add_handler(CommandHandler('book', book_slot))

    # run_polling in modo sincrono
    application.run_polling()

if __name__ == '__main__':
    main()
