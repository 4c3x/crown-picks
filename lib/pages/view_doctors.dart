import 'package:flutter/material.dart';

class ViewDoctors extends StatelessWidget {
  const ViewDoctors({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Text('View Doctors Page Content Here',
        style: TextStyle(
          fontSize: 24,
        ),),
      ),
    );
  }
}