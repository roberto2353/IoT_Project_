import 'package:flutter/material.dart';
import 'dart:math';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Parking Kiosk',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: MyHomePage(),
    );
  }
}

class MyHomePage extends StatefulWidget {
  @override
  _MyHomePageState createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  final TextEditingController _controller = TextEditingController();
  bool _isError = false;
  List<dynamic> _parkings = [];  // Lista di parcheggi caricata dal catalogo
  String? _selectedParking; // Parcheggio selezionato


  // Funzione per recuperare i parcheggi dal catalogo
  Future<void> _fetchParkings() async {
    try {
      final response = await http.get(Uri.parse('http://localhost:8090/parkings'));  // Sostituisci con l'URL del tuo catalogo
      if (response.statusCode == 200) {
        setState(() {
          _parkings = jsonDecode(response.body)['parkings'];
        });
      } else {
        throw Exception('Failed to load parkings');
      }
    } catch (e) {
      print("Error fetching parkings: $e");
    }
  }

  // Carica i parcheggi all'avvio dell'app
  @override
  void initState() {
    super.initState();
    _fetchParkings();
  }



  void verifyBooking() {
    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text("Insert Booking Code"),
              IconButton(
                icon: Icon(Icons.close),
                onPressed: () {
                  _controller.clear();  // Pulisce il campo di testo
                  setState(() {
                    _isError = false;
                  });
                  Navigator.of(ctx).pop();
                },
              ),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: _controller,
                decoration: InputDecoration(hintText: "Booking Code"),
              ),
              if (_isError)
                Padding(
                  padding: const EdgeInsets.only(top: 8.0),
                  child: Text(
                    "Booking code is incorrect. Please try again.",
                    style: TextStyle(color: Colors.red),
                  ),
                ),
            ],
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () async {
                String code = _controller.text;

                // Trova il parcheggio selezionato per ottenere URL e porta
                var parking = _parkings.firstWhere(
                        (p) => p['ID'].toString() == _selectedParking,
                    orElse: () => null);

                if (parking == null) {
                  setState(() {
                    _isError = true;
                  });
                  _controller.clear();
                  Navigator.of(ctx).pop();
                  return;
                }

                // Crea il corpo della richiesta con i dettagli del parcheggio selezionato
                var data = {
                  "booking_code": code,
                  "url": parking['url'],
                  "port": parking['port']
                };

                var response = await http.post(
                  Uri.parse('http://localhost:8085/activate'),  // URL del backend
                  headers: {"Content-Type": "application/json"},
                  body: jsonEncode(data),
                );

                if (response.statusCode == 200) {
                  var responseData = jsonDecode(response.body);
                  _controller.clear();

                  Navigator.of(ctx).pop();

                  showDialog(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text("Reply"),
                          IconButton(
                            icon: Icon(Icons.close),
                            onPressed: () {
                              Navigator.of(ctx).pop();
                            },
                          ),
                        ],
                      ),
                      content: Text(responseData['message']),
                      actions: <Widget>[
                        TextButton(
                          onPressed: () {
                            Navigator.of(ctx).pop();
                          },
                          child: Text("OK"),
                        ),
                      ],
                    ),
                  );
                } else {
                  setState(() {
                    _isError = true;
                  });
                  _controller.clear();
                }
              },
              child: Text("Verify"),
            ),
          ],
        );
      },
    );
  }

  void bookNow() {
    Random random = Random();
    String bookingCode = String.fromCharCodes(
        List.generate(6, (index) => random.nextInt(26) + 65));

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text("Book Now"),
            IconButton(
              icon: Icon(Icons.close),
              onPressed: () {
                Navigator.of(ctx).pop();
              },
            ),
          ],
        ),
        content: Text("Your booking code is : $bookingCode"),
        actions: <Widget>[
          TextButton(
            onPressed: () async {
              // Trova il parcheggio selezionato
              var parking = _parkings.firstWhere(
                    (p) => p['ID'].toString() == _selectedParking,
                orElse: () => null,
              );

              if (parking == null) {
                // Mostra un messaggio di errore se nessun parcheggio è selezionato
                Navigator.of(ctx).pop();
                showDialog(
                  context: context,
                  builder: (ctx) => AlertDialog(
                    title: Text("Error"),
                    content: Text("Please select a parking lot before booking."),
                    actions: <Widget>[
                      TextButton(
                        child: Text("OK"),
                        onPressed: () {
                          Navigator.of(ctx).pop();
                        },
                      ),
                    ],
                  ),
                );
                return;
              }

              // Crea il corpo della richiesta con i dettagli del parcheggio selezionato
              var data = {
                'url': 'http://${parking['url']}:${parking['port']}/get_best_parking',
                'booking_code': bookingCode,
              };

              var response = await http.post(
                Uri.parse('http://localhost:8098/book'),  // URL del backend per creare la prenotazione
                headers: {"Content-Type": "application/json"},
                body: jsonEncode(data),
              );

              Navigator.of(ctx).pop();

              showDialog(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text("Results"),
                      IconButton(
                        icon: Icon(Icons.close),
                        onPressed: () {
                          Navigator.of(ctx).pop();
                        },
                      ),
                    ],
                  ),
                  content: Text(response.statusCode == 200
                      ? jsonDecode(response.body)['message']
                      : "Error occurred. Please try again"),
                  actions: <Widget>[
                    TextButton(
                      onPressed: () {
                        Navigator.of(ctx).pop();
                      },
                      child: Text("OK"),
                    ),
                  ],
                ),
              );
            },
            child: Text("OK"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Parking Kiosk'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 50.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Text(
                'Select Parking Lot:',
                style: TextStyle(fontSize: 18),
              ),
              SizedBox(height: 10),
              DropdownButton<String>(
                value: _selectedParking,
                hint: Text("Select Parking"),
                items: _parkings.map((parking) {
                  return DropdownMenuItem<String>(
                    value: parking['ID'].toString(),
                    child: Text(parking['name']),
                  );
                }).toList(),
                onChanged: (value) {
                  setState(() {
                    _selectedParking = value;
                  });
                },
              ),
              SizedBox(height: 20),

              Container(
                padding: EdgeInsets.all(12),
                margin: EdgeInsets.only(bottom: 20.0),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.blueAccent), // Cornice
                  borderRadius: BorderRadius.circular(10),
                ),
                child: RichText(
                  textAlign: TextAlign.center,
                  text: TextSpan(
                    style: TextStyle(fontSize: 16, color: Colors.black),
                    children: [
                      TextSpan(
                        text: 'Do you have a reservation?\n',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      TextSpan(
                        text: ' Please press the button and insert your booking code.',
                      ),
                    ],
                  ),
                ),
              ),
              ElevatedButton(
                onPressed: verifyBooking,
                style: ElevatedButton.styleFrom(
                  padding: EdgeInsets.symmetric(horizontal: 50, vertical: 20),  // Dimensioni pulsante
                  textStyle: TextStyle(fontSize: 20),
                ),
                child: Text('Verify Booking'),
              ),

              Container(
                padding: EdgeInsets.all(12),
                margin: EdgeInsets.symmetric(vertical: 20.0),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.green), // Cornice
                  borderRadius: BorderRadius.circular(10),
                ),
                child: RichText(
                  textAlign: TextAlign.center,
                  text: TextSpan(
                    style: TextStyle(fontSize: 16, color: Colors.black),
                    children: [
                      TextSpan(
                        text: "No reservation?\n",
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      TextSpan(
                        text: " Don't Worry you can book now your slot if available.",
                      ),
                    ],
                  ),
                ),
              ),
              ElevatedButton(
                onPressed: bookNow,
                style: ElevatedButton.styleFrom(
                  padding: EdgeInsets.symmetric(horizontal: 50, vertical: 20),  // Dimensioni pulsante
                  textStyle: TextStyle(fontSize: 20),
                ),
                child: Text('Book now'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}