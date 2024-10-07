import requests
import json

# URL del server CherryPy
url = 'http://127.0.0.1:8056/exit' 

# Dati da inviare nella richiesta
data = {
    "booking_code": "119b8001-9ca5-48ff-841a-a93d21b9106b"
}

# Invio della richiesta POST
response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))

# Stampa la risposta del server
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
