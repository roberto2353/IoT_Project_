# 🚗 IoT SmartParking

**IoT SmartParking** is an IoT-based parking management system that uses **MQTT** for device communication, **CherryPy** as the backend service, and a **Telegram bot** for user interaction. The system allows users to check parking slot availability, make reservations, and calculate parking fees.

---

## 📋 Features

1. **Real-time Parking Slot Management**  
   - Monitors free and occupied parking slots.  
   - Updates slot status dynamically using MQTT.

2. **Parking Slot Reservations**  
   - Users can reserve parking slots via RESTful APIs or the Telegram bot.  
   - The system updates slot availability in real-time.

3. **Exit Management with Fee Calculation**  
   - Calculates parking fees based on entry and exit times.  
   - Stores time-series data in **InfluxDB**.

4. **User Wallet and Recent Transactions**  
   - Provides users with a wallet feature to view recent transactions.  
   - Managed via the Telegram bot.
  
5. **Parking Entrance kiosk App**  
   App allows users to check and reserve available parking slots in real time. Once a slot is selected, the app registers the reservation by sending the data to the backend. Slot availability is dynamically updated, and the app ensures a user-friendly interface for a seamless experience..
  
6. **Parking Exit kiosk App**  
   App enables users to enter their booking code received during entry and calculates the total amount to be paid based on the parking duration. It displays a pop-up with the total in euros and automatically updates the slot status to "available" once the exit process is completed

---

## 🛠️ System Architecture

The project consists of the following components:

### 1. **Backend (CherryPy)**
- A RESTful API developed with **CherryPy** to manage:
  - Slot availability.
  - User reservations.
  - Parking exit and fee calculations.

### 2. **Communication (MQTT)**
- Devices use the **Paho MQTT** library to:
  - Send updates for parking slot status.
  - Receive commands and notifications.

### 3. **Database (InfluxDB)**
- **InfluxDB** is used for time-series data to store:
  - Entry and exit times of vehicles.
  - Parking sensor updates.

### 4. **Telegram Bot (ParkingBot)**
- A Telegram bot developed using **Telepot** that allows users to:
  - Check available slots.
  - Make reservations.
  - View their wallet with recent transactions.

---

## 📦 Installation

Follow these steps to set up the project locally:

### **Prerequisites**
Ensure you have the following installed:
- Python 3.10+
- MQTT Broker (e.g., Mosquitto)
- InfluxDB 1.x
- Telegram Bot API Token

### **1. Clone the Repository**
git clone https://github.com/yourusername/IoT-SmartParking.git
cd IoT_Project_

### 2. Install Dependencies

Use `pip` to install the required libraries:
pip install -r requirements.txt

### 3. Configure the System

Edit the `config.json` file to include:

- **MQTT Broker Details** (host, port, username, password)
- **InfluxDB Credentials**
- **Telegram Bot API Token**

Example `config.json`:
{
  "mqtt": {
    "broker": "localhost",
    "port": 1883
  },
  "influxdb": {
    "host": "localhost",
    "port": 8086,
    "database": "parking_data"
  },
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN"
  }
}

### 4. Run the Backend Service

Start the CherryPy backend server by running the following command:
python name_service.py

## 📡 MQTT Topics

| Topic               | Description                        |
|---------------------|------------------------------------|
| `parking/device/status`    | Updates slot availability status on InfluxDb |
| `parking/deviceConnector/device/status`    | Updates and control slot availability status |
| `parking/device/alive`     | Devices updates                | 
| `parking/service/alive`      | Services time updates                 |

---





