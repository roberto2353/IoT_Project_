import requests
import json

# URL del server CherryPy
url = 'http://127.0.0.1:8085/activate'

# Dati da inviare nella richiesta
data = {
    "booking_code": "d5d30b"

}

# Invio della richiesta POST
response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))

# Stampa la risposta del server
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
