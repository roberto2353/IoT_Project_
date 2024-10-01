import requests
import json

# URL del server CherryPy
url = 'http://127.0.0.1:8085/activate' 

# Dati da inviare nella richiesta
data = {
    "booking_code": "27418abb-8c5b-49a7-ad67-93b143f71a5b"
}

# Invio della richiesta POST
response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))

# Stampa la risposta del server
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
