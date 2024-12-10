import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:ui';

void main() {
  runApp(ParkingExitApp());
}

// Main application widget with MaterialApp configuration
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

// Stateful widget to manage parking exit functionality
class ParkingExitScreen extends StatefulWidget {
  @override
  _ParkingExitScreenState createState() => _ParkingExitScreenState();
}

class _ParkingExitScreenState extends State<ParkingExitScreen> {
  final _controller = TextEditingController(); // Text controller for booking code input
  bool _isLoading = false; // Indicates loading state during operations
  bool _isError = false; // Tracks error state
  List<Map<String, dynamic>> _parkings = []; // List of available parking lots
  String? _selectedParking; // Stores the selected parking ID
  String? _selectedParkingName; // Stores the selected parking name

  // Fetches parking data from the server
  Future<void> _fetchParkings() async {
    try {
      final response = await http.get(Uri.parse('http://localhost:8090/parkings'));
      if (response.statusCode == 200) {
        setState(() {
          _parkings = (jsonDecode(response.body)['parkings'] as List)
              .map((parking) => parking as Map<String, dynamic>)
              .toList();
        });
        // Shows the parking selection dialog
        Future.delayed(Duration.zero, _showParkingSelectionDialog);
      } else {
        throw Exception('Failed to load parkings');
      }
    } catch (e) {
      print("Error fetching parkings: $e");
    }
  }

  // Initializes parking data fetch on widget load
  @override
  void initState() {
    super.initState();
    _fetchParkings();
  }

  // Displays a dialog to select a parking lot
  void _showParkingSelectionDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return AlertDialog(
          title: Text("Select Parking Lot"),
          content: Material(
            color: Colors.transparent,
            child: Container(
              decoration: BoxDecoration(
                border: Border.all(color: Colors.blueAccent),
                borderRadius: BorderRadius.circular(10), // Arrotonda i bordi del dialogo
              ),
              child: DropdownButton<String>(
                value: _selectedParking,
                hint: Text("Select Parking"),
                isExpanded: true,
                underline: SizedBox(), // Rimuove la sottolineatura di default
                items: _parkings.map((parking) {
                  return DropdownMenuItem<String>(
                    value: parking['ID'].toString(),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(10), // Arrotonda le voci del menu
                      child: Container(
                        padding: EdgeInsets.symmetric(vertical: 10.0, horizontal: 16.0),
                        child: Text(parking['name']),
                      ),
                    ),
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
            ),
          ),
        );
      },
    );
  }




  // Submits the booking code for processing
  Future<void> _submitCode(String bookingCode) async {
    setState(() {
      _isLoading = true;
      _isError = false;
    });

    var parking = _parkings.firstWhere(
          (p) => p['ID'].toString() == _selectedParking,
      orElse: () => {},
    );

    if (parking.isEmpty) {
      _showErrorDialog('Select a valid parking lot.');
      setState(() {
        _isLoading = false;
      });
      return;
    }

    final url = 'http://localhost:8056/exit';
    final response = await http.post(
      Uri.parse(url),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'booking_code': bookingCode,
        'url': parking['url'],
        'port': parking['port'],
        'name': parking['name'],
        'parking': _selectedParkingName,
      }),
    );

    setState(() {
      _isLoading = false;
    });

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      if (data.containsKey('error')) {
        _showErrorDialog(data['error']);
      } else {
        // Parses response data
        final duration = data['parking_duration'] is String
            ? data['parking_duration']
            : data['parking_duration'].toString();
        final fee = data['parking_fee'];

        _showResultDialog(duration, fee);
      }
    } else {
      _showErrorDialog('There was an error. Please try again.');
    }
  }

  // Displays the parking duration and fee result
  void _showResultDialog(String duration, double fee) {
    double roundedFee = double.parse(fee.toStringAsFixed(2)); // Rounds fee to 2 decimals
    double durationInHours = double.parse(duration); // Converts duration to hours

    // Formats the duration in hours and minutes
    String formattedDuration;
    if (durationInHours < 1) {
      int minutes = (durationInHours * 60).round();
      formattedDuration = "$minutes minutes";
    } else {
      int hours = durationInHours.floor();
      int minutes = ((durationInHours - hours) * 60).round();
      if (minutes == 0) {
        formattedDuration = "$hours hours";
      } else {
        formattedDuration = "$hours hours and $minutes minutes";
      }
    }

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Amount and Duration'),
            IconButton(
              icon: Icon(Icons.close),
              onPressed: () {
                Navigator.of(ctx).pop();
              },
            ),
          ],
        ),
        content: Text('Duration: $formattedDuration\nAmount: €$roundedFee'),
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

  // Displays an error dialog with a custom message
  void _showErrorDialog(String message) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Error'),
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

  // Main screen layout for booking code input and actions
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10.0, sigmaY: 10.0),
          child: Text(
            'Parking Kiosk - Exit',
            style: TextStyle(color: Colors.white),
          ),
        ),
        centerTitle: true,
        backgroundColor: Colors.blueAccent.withOpacity(0.8),
        elevation: 6,
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 20.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              if (_selectedParkingName != null)
                Column(
                  children: [
                    Text(
                      'GOODBYE!',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        color: Colors.black87,
                      ),
                    ),
                    SizedBox(height: 10),
                    Text(
                      'You are exiting from: $_selectedParkingName',
                      style: TextStyle(
                        fontSize: 18,
                        fontStyle: FontStyle.italic,
                        color: Colors.black87,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    SizedBox(height: 10),
                    Text(
                      'Please insert your booking code to pay and exit.',
                      style: TextStyle(fontSize: 16, color: Colors.black87),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              SizedBox(height: 20),
              Container(
                width: 280,
                height: 50,
                padding: EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.black.withOpacity(0.6), width: 1.5),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Center(
                  child: TextField(
                    controller: _controller,
                    decoration: InputDecoration(
                      hintText: 'Insert your booking code',
                      border: InputBorder.none,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
              SizedBox(height: 15),
              SizedBox(
                width: 140,
                height: 50,
                child: ElevatedButton(
                  onPressed: () {
                    final code = _controller.text;
                    if (code.isEmpty) {
                      _showErrorDialog('Insert a valid booking code.');
                    } else {
                      _submitCode(code);
                    }
                  },
                  style: ButtonStyle(
                    foregroundColor: MaterialStateProperty.all(Colors.black), // Testo nero
                    backgroundColor: MaterialStateProperty.all(Colors.white), // Sfondo bianco
                    shadowColor: MaterialStateProperty.all(Colors.grey.withOpacity(0.5)), // Ombra grigia
                    overlayColor: MaterialStateProperty.resolveWith<Color?>(
                          (states) {
                        if (states.contains(MaterialState.pressed)) {
                          return Colors.grey.withOpacity(0.2); // Colore premuto
                        }
                        return null;
                      },
                    ),
                    side: MaterialStateProperty.all(
                      BorderSide(color: Colors.black, width: 2), // Bordo nero
                    ),
                    textStyle: MaterialStateProperty.all(
                      TextStyle(
                        fontSize: 16,
                        letterSpacing: 1.2,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    shape: MaterialStateProperty.all(
                      RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                  ),
                  child: Text('Pay & Exit'),
                ),
              ),

              if (_isLoading)
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: CircularProgressIndicator(),
                ),
              SizedBox(height: 30),
              Text(
                'Thank you for using our parking. See you again!',
                style: TextStyle(
                  fontSize: 18,
                  fontStyle: FontStyle.italic,
                  color: Colors.blueAccent,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

}
