from influxdb import InfluxDBClient

def delete_all_sensors():
    try:
        # Connessione a InfluxDB
        client = InfluxDBClient(host='localhost', port=8086, username='root', password='root', database='IoT_Smart_Parking')

        # Query per cancellare tutti i punti dalla misura "status"
        delete_query = 'DELETE FROM "status"'
        client.query(delete_query)
        
        print("Tutti i sensori sono stati cancellati dal database.")
    
    except Exception as e:
        print(f"Errore durante la cancellazione dei sensori: {e}")

# Esegui la funzione per cancellare i dati
delete_all_sensors()
