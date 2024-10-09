import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(ParkingExitApp());
}

class ParkingExitApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Parking Exit',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: ParkingExitScreen(),
    );
  }
}

class ParkingExitScreen extends StatefulWidget {
  @override
  _ParkingExitScreenState createState() => _ParkingExitScreenState();
}

class _ParkingExitScreenState extends State<ParkingExitScreen> {
  final _controller = TextEditingController();
  bool _isLoading = false;
  bool _isError = false;

  Future<void> _submitCode(String bookingCode) async {
    setState(() {
      _isLoading = true;
      _isError = false;
    });

    final url = 'http://172.20.10.8:8056/exit';
    final response = await http.post(
      Uri.parse(url),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'booking_code': bookingCode}),
    );

    setState(() {
      _isLoading = false;
    });

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      if (data.containsKey('error')) {
        _showErrorDialog(data['error']);
      } else {
        _showResultDialog(data['parking_duration'], data['parking_fee']);
      }
    } else {
      _showErrorDialog('Si è verificato un errore. Riprovare.');
    }
  }

  void _showResultDialog(String duration, double fee) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Importo da pagare'),
            IconButton(
              icon: Icon(Icons.close),
              onPressed: () {
                Navigator.of(ctx).pop();
              },
            ),
          ],
        ),
        content: Text('Durata: $duration\nImporto: €$fee'),
        actions: [
          TextButton(
            child: Text('OK'),
            onPressed: () {
              Navigator.of(ctx).pop();
            },
          ),
        ],
      ),
    );
  }

  void _showErrorDialog(String message) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Errore'),
            IconButton(
              icon: Icon(Icons.close),
              onPressed: () {
                Navigator.of(ctx).pop();
              },
            ),
          ],
        ),
        content: Text(message),
        actions: [
          TextButton(
            child: Text('OK'),
            onPressed: () {
              Navigator.of(ctx).pop();
            },
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Uscita Parcheggio'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 50.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              // TextField con dimensioni fisse simili ai bottoni
              Container(
                width: 300,  // Larghezza fissa
                height: 60,  // Altezza fissa
                padding: EdgeInsets.symmetric(horizontal: 20),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.blueAccent),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Center(
                  child: TextField(
                    controller: _controller,
                    decoration: InputDecoration(
                      hintText: 'Inserisci codice prenotazione',
                      border: InputBorder.none,
                    ),
                    textAlign: TextAlign.center,  // Allinea il testo al centro
                  ),
                ),
              ),
              SizedBox(height: 20),
              // Bottone con dimensioni fisse
              SizedBox(
                width: 300,  // Larghezza fissa
                height: 60,  // Altezza fissa
                child: ElevatedButton(
                  onPressed: () {
                    final code = _controller.text;
                    if (code.isEmpty) {
                      _showErrorDialog('Inserisci un codice di prenotazione valido.');
                    } else {
                      _submitCode(code);
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    padding: EdgeInsets.symmetric(horizontal: 50, vertical: 20),
                    textStyle: TextStyle(fontSize: 20),
                  ),
                  child: Text('Calcola Importo'),
                ),
              ),
              if (_isLoading)
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: CircularProgressIndicator(),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
