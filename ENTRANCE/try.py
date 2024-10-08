import requests
import json

# URL del server CherryPy
url = 'http://127.0.0.1:8056/exit' 

# Dati da inviare nella richiesta
data = {
    "booking_code": "85f410f7-25c0-4a33-962b-2a936d33d7ee"
}

# Invio della richiesta POST
response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))

# Stampa la risposta del server
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
