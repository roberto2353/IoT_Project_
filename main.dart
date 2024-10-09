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

  // Funzione per visualizzare pop-up con TextField
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


                var data = {
                  "booking_code": code
                };


                var response = await http.post(
                  Uri.parse('http://172.20.10.8:8085/activate'),  // URL  backend
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
                  // Se il codice non è corretto
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

  // Funzione per generare un codice di prenotazione se non ce l'ha l'utente
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
              // Invio della richiesta HTTP per creare la prenotazione
              var data = {
                "booking_code": bookingCode
              };

              var response = await http.post(
                Uri.parse('http://127.0.0.1:8085/create_booking'),  // URL del backend per creare la prenotazione
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
