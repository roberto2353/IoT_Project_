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
```bash
git clone https://github.com/yourusername/IoT-SmartParking.git
cd IoT-SmartParking
