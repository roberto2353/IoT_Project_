import requests
import json

# URL del server CherryPy
<<<<<<< HEAD
url = 'http://127.0.0.1:8056/exit' 

# Dati da inviare nella richiesta
data = {
    "booking_code": "119b8001-9ca5-48ff-841a-a93d21b9106b"
=======
url = 'http://127.0.0.1:8056/exit'

# Dati da inviare nella richiesta
data = {
    "booking_code": "7e931151-ee52-4c1d-abf1-6f1179a12722"
>>>>>>> c1e4c2d5cc485d8fd8b48cfca465f2871a2d801c
}

# Invio della richiesta POST
response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))

# Stampa la risposta del server
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
