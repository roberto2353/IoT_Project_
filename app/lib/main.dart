import 'package:flutter/material.dart';
import 'dart:math';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:ui';

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
        textTheme: TextTheme(
          // Aggiorniamo i parametri del tema con i nuovi nomi
          bodyLarge: TextStyle(fontFamily: 'Roboto', fontSize: 16, color: Colors.black87),
          bodyMedium: TextStyle(fontFamily: 'Roboto', fontSize: 16, color: Colors.black),
          titleLarge: TextStyle(fontFamily: 'Roboto', fontSize: 22, fontWeight: FontWeight.bold), // Sostituito headline6
        ),
        buttonTheme: ButtonThemeData(
          buttonColor: Colors.blueAccent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          contentPadding: EdgeInsets.symmetric(vertical: 18, horizontal: 15),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide(color: Colors.blueAccent),
          ),
        ),
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
  List<Map<String, dynamic>> _parkings = [];
  String? _selectedParking;
  String? _selectedParkingName;

  // Funzione per recuperare i parcheggi dal catalogo
  Future<void> _fetchParkings() async {
    try {
      final response = await http.get(Uri.parse('http://localhost:8090/parkings'));
      if (response.statusCode == 200) {
        setState(() {
          _parkings = (jsonDecode(response.body)['parkings'] as List)
              .map((parking) => parking as Map<String, dynamic>)
              .toList();
        });
        //  Finestra di selezione parcheggio
        Future.delayed(Duration.zero, _showParkingSelectionDialog);
      } else {
        throw Exception('Failed to load parkings');
      }
    } catch (e) {
      print("Error fetching parkings: $e");
    }
  }

  @override
  void initState() {
    super.initState();
    _fetchParkings();
  }

  void _showParkingSelectionDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return AlertDialog(
          title: Text("Select Parking Lot"),
          content: DropdownButton<String>(
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
                _selectedParkingName = _parkings
                    .firstWhere((p) => p['ID'].toString() == value)['name'];
              });
              Navigator.of(ctx).pop();
            },
          ),
        );
      },
    );
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
                  _controller.clear();
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
                var parking = _parkings.firstWhere(
                        (p) => p['ID'].toString() == _selectedParking,
                    orElse: () => {});

                if (parking.isEmpty) {
                  setState(() {
                    _isError = true;
                  });
                  _controller.clear();
                  Navigator.of(ctx).pop();
                  return;
                }

                var data = {
                  "booking_code": code,
                  "url": parking['url'],
                  "port": parking['port'],
                  "name": parking['name']
                };

                var response = await http.post(
                  Uri.parse('http://localhost:8085/activate'),
                  headers: {"Content-Type": "application/json"},
                  body: jsonEncode(data),
                );

                Navigator.of(ctx).pop();

                if (response.statusCode == 200) {
                  var responseData = jsonDecode(response.body);
                  _controller.clear();
                  showDialog(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: Text("Reply"),
                      content: Text(responseData['message'] ?? 'Operation successful'),
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
    String bookingCode = generateBookingCode();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text("Book Now"),
        content: Text("Your booking code is: $bookingCode"),
        actions: <Widget>[
          TextButton(
            onPressed: () async {
              var parking = _parkings.firstWhere(
                      (p) => p['ID'].toString() == _selectedParking,
                  orElse: () => {});

              if (parking.isEmpty) {
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

              var data = {
                'url': 'http://${parking['url']}:${parking['port']}/get_best_parking',
                'port': parking['port'],
                '_url': parking['url'],
                'booking_code': bookingCode,
                'name': parking['name']

              };

              var response = await http.post(
                Uri.parse('http://localhost:8098/book'),
                headers: {"Content-Type": "application/json"},
                body: jsonEncode(data),
              );

              Navigator.of(ctx).pop();

              showDialog(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: Text("Results"),
                  content: Text(response.statusCode == 200
                      ? jsonDecode(response.body)['message'] ?? 'Booking successful'
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

  String generateBookingCode() {
    Random random = Random();
    return String.fromCharCodes(
        List.generate(6, (index) => random.nextInt(26) + 65));
  }



  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10.0, sigmaY: 10.0),
          child: Text(
            'Parking Kiosk',
            style: TextStyle(color: Colors.white),
          ),
        ),
        centerTitle: true,
        backgroundColor: Colors.blueAccent.withOpacity(0.8),
        elevation: 6,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Center(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: <Widget>[
              if (_selectedParkingName != null)
                Column(
                  children: [
                    Text(
                      'Hello!',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        color: Colors.black87,
                      ),
                    ),
                    SizedBox(height: 10),
                    Text(
                      'Welcome to $_selectedParkingName parking lot!',
                      style: TextStyle(
                        fontSize: 18,
                        fontStyle: FontStyle.italic,
                        color: Colors.black87,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    SizedBox(height: 10),
                    Text(
                      'You can book a parking spot now or verify your booking code.',
                      style: TextStyle(fontSize: 16, color: Colors.black87),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              SizedBox(height: 30),
              buildSection(
                "Do you have a booking code?",
                "\nInsert your booking code to verify your booking.",
                verifyBooking,
              ),
              buildSection(
                "You don't have a booking code?",
                "\nYou can book a parking spot now if there are available spots.",
                bookNow,
              ),
              SizedBox(height: 20),
              Divider(color: Colors.grey),
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 20.0),
                child: Text(
                  'We recommend booking in advance the next time to secure a spot and save your time \nusing our telegram bot : ''PARKINGPROJECT''!',
                  style: TextStyle(
                    fontSize: 16,
                    fontStyle: FontStyle.italic,
                    color: Colors.blueAccent,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget buildSection(String title, String message, VoidCallback onPressed) {
    return Column(
      children: [
        Container(
          padding: EdgeInsets.all(18),
          margin: EdgeInsets.symmetric(vertical: 12.0),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(
              color: title.contains("reservation")
                  ? Colors.blueAccent
                  : Colors.black,
            ),
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                  blurRadius: 8,
                  spreadRadius: 2,
                  color: Colors.grey.withOpacity(0.2))
            ],
          ),
          child: RichText(
            textAlign: TextAlign.center, // Centra tutto il testo
            text: TextSpan(
              style: TextStyle(fontSize: 18, color: Colors.black),
              children: [
                TextSpan(
                  text: "$title\n",
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),

                TextSpan(text: message),
              ],
            ),
          ),
        ),
        ElevatedButton(
          onPressed: onPressed,
          style: ElevatedButton.styleFrom(
            padding: EdgeInsets.symmetric(horizontal: 60, vertical: 18),
            textStyle: TextStyle(fontSize: 18, letterSpacing: 1.2),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(color: Colors.black, width: 2)),
            foregroundColor: Colors.black,
            backgroundColor: Colors.white,
          ),
          child: Text(
            title.contains("Do you have a booking code?")
                ? 'Insert it'
                : 'Book now', // Cambia il testo in base al titolo
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
      ],
    );
  }



}
