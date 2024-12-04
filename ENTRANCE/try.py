import requests
import json

# CherryPy URL server
url = 'http://127.0.0.1:8056/exit'

# Data to send on request
data = {
    "booking_code": "5e3e0825-4588-48e3-8354-f5e4ff211dae",
    "url":"dev_conn_1",
    "port":8083,
    "name":'DevConnector1'

}

# POST request
response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))
print(f"Status Code: {response.status_code}")
